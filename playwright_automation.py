import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional
import json
import time
from logger import uat_logger
import ctypes  # 用于调用Windows API获取真实屏幕尺寸

class PlaywrightAutomation:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.recording = False
        self.recorded_steps = []
        self.current_url = ""
        self.page_events = []  # 存储页面事件以便后续处理
        self.sync_task = None  # 用于同步录制事件的后台任务
        self.playwright = None  # 初始化playwright实例变量
    
    async def start_browser(self, headless=False):
        """启动浏览器"""
        try:
            if self.browser is None:
                uat_logger.info(f"启动浏览器，headless={headless}")
                
                # 1. 使用Windows API直接获取真实的屏幕尺寸（不依赖浏览器）
                self.playwright = await async_playwright().start()
                
                # 调用Windows API获取真实屏幕尺寸
                user32 = ctypes.windll.user32
                # 获取主显示器的屏幕尺寸
                screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                
                # 获取可用工作区尺寸（减去任务栏等）
                avail_width = user32.GetSystemMetrics(78)  # SM_CXAVAILABLE
                avail_height = user32.GetSystemMetrics(79)  # SM_CYAVAILABLE
                
                screen_size = {"width": screen_width, "height": screen_height}
                avail_screen_size = {"width": avail_width, "height": avail_height}
                
                uat_logger.info(f"Windows API获取的屏幕尺寸: {screen_size['width']}x{screen_size['height']}")
                uat_logger.info(f"Windows API获取的可用工作区尺寸: {avail_screen_size['width']}x{avail_screen_size['height']}")
                
                # 2. 使用获取到的可用工作区尺寸启动真正的浏览器实例
                # 使用可用工作区尺寸可以避免与任务栏等系统UI冲突
                args = [
                    '--start-maximized',  # 真正的浏览器最大化
                    '--no-default-browser-check',
                    '--no-first-run'
                ]
                
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=args
                )
                
                # 创建上下文时不强制设置viewport大小，让浏览器自动适应窗口尺寸
                # 这样可以确保页面渲染和滚动行为与普通浏览器一致
                self.context = await self.browser.new_context(
                    ignore_https_errors=True,
                    no_viewport=True  # 让浏览器自动管理视口大小
                )
                
                # 创建新页面
                self.page = await self.context.new_page()
                
                # 使用Windows API获取真实屏幕尺寸
                user32 = ctypes.windll.user32
                screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                
                # 设置浏览器窗口大小为真实屏幕尺寸
                uat_logger.info(f"将浏览器窗口设置为真实屏幕尺寸: {screen_width}x{screen_height}")
                await self.page.evaluate(f"window.resizeTo({screen_width}, {screen_height})")
                await self.page.evaluate("window.moveTo(0, 0)")
                
                # 直接获取浏览器窗口的实际尺寸
                viewport_size = await self.page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                outer_size = await self.page.evaluate("() => ({ width: window.outerWidth, height: window.outerHeight })")
                screen_size = await self.page.evaluate("() => ({ width: screen.width, height: screen.height })")
                avail_screen_size = await self.page.evaluate("() => ({ width: screen.availWidth, height: screen.availHeight })")
                
                uat_logger.info(f"屏幕总尺寸: {screen_size['width']}x{screen_size['height']}")
                uat_logger.info(f"屏幕可用尺寸: {avail_screen_size['width']}x{avail_screen_size['height']}")
                uat_logger.info(f"浏览器窗口内尺寸: {viewport_size['width']}x{viewport_size['height']}")
                uat_logger.info(f"浏览器窗口外尺寸: {outer_size['width']}x{outer_size['height']}")
                uat_logger.info(f"浏览器已设置为全屏模式，右上角最大化按钮应不可见")
                
                uat_logger.info("浏览器已启动并最大化，设置事件监听器")
                
                # 设置事件监听器用于录制用户操作
                await self._setup_event_listeners()
                
                # 监听页面跳转事件，确保在新页面上也设置事件监听器
                self.page.on('framenavigated', self._on_page_navigated)
            
            return self.page
        except Exception as e:
            uat_logger.log_exception("start_browser", e)
            raise Exception(f"启动浏览器失败: {str(e)}")
    
    async def _setup_event_listeners(self):
        """设置页面事件监听器用于录制操作"""
        if self.page:
            # 定义事件监听器JavaScript代码
            event_listeners_js = r"""
                // 检查是否已经添加了事件监听器，避免重复添加
                if (!window.eventListenersAdded) {
                    // 初始化事件数组
                    window.automationEvents = window.automationEvents || [];
                    window.automationConfig = {
                        scrollTimeout: null,
                        lastScrollPosition: { x: 0, y: 0 },
                        scrollThreshold: 50, // 只有滚动超过50px才记录
                        inputDebounce: {},
                        debounceDelay: 500
                    };
                
                // 生成更精确的CSS选择器
                // 递归辅助函数：生成元素的完整路径选择器
                function generateFullPath(element, maxDepth = 4, currentDepth = 0) {
                    if (!element || element.tagName === 'HTML' || currentDepth >= maxDepth) {
                        return [];
                    }
                    
                    let elementSelector = '';
                    const tagName = element.tagName.toLowerCase();
                    
                    // 优先使用ID
                    if (element.id) {
                        return [`#${element.id}`];
                    }
                    
                    // 优先使用稳定属性 - 扩展更多自动化测试常用属性
                    const stableAttrs = [
                        'data-testid', 'data-cy', 'data-test', 'data-qa', 
                        'data-automation', 'data-selector', 'data-key', 
                        'data-id', 'data-name', 'data-component', 
                        'data-module', 'data-section', 'data-field',
                        'data-action', 'data-target', 'data-type',
                        'name', 'title', 'role', 'aria-label', 
                        'aria-labelledby', 'aria-describedby', 'aria-controls'
                    ];
                    let hasStableAttr = false;
                    for (const attr of stableAttrs) {
                        const value = element.getAttribute(attr);
                        if (value && value.length > 0 && !value.includes(' ')) {
                            elementSelector = `${tagName}[${attr}="${value}"]`;
                            hasStableAttr = true;
                            break;
                        }
                    }
                    
                    if (!hasStableAttr) {
                        elementSelector = tagName;
                        // 处理类名，过滤掉动态类名
                        if (element.className) {
                            const allClasses = element.className.split(' ').filter(c => c.length > 2); // 过滤掉太短的类名
                            const dynamicClassPatterns = [
                                /^is-\w+$/, /^has-\w+$/, /^\w+-\w+-(leave|enter|active|done)$/, 
                                /^el-\w+(-\w+)*$/, /^ant-\w+(-\w+)*$/, /^t-[a-zA-Z0-9]{8}$/, 
                                /^weui-\w+(-\w+)*$/, /^layui-\w+(-\w+)*$/, /^v-\w+$/, 
                                /^ng-\w+$/, /^vue-\w+$/, /^react-\w+$/, /^svelte-\w+$/, 
                                /^css-\w+$/, /^scss-\w+$/, /^style-\w+$/, /^component-\w+$/, 
                                /^theme-\w+$/, /^mode-\w+$/, /^state-\w+$/, /^variant-\w+$/, 
                                /^hover-\w+$/, /^focus-\w+$/, /^active-\w+$/, /^disabled-\w+$/, 
                                /^selected-\w+$/, /^checked-\w+$/, /^expanded-\w+$/, /^collapsed-\w+$/, /^open-\w+$/, /^closed-\w+$/, 
                                /^loading-\w+$/, /^error-\w+$/, /^success-\w+$/, /^warning-\w+$/, /^info-\w+$/, 
                                /^\d+-\w+$/, /^\w+-\d+$/, /^[a-f0-9]{6,}$/, /^\w+-[a-f0-9]{6,16}$/, 
                                /^\w+-[0-9a-z]{8,}$/, /^[a-z]{3,6}-[0-9a-z]{5,10}$/, 
                                /^v?\d+\.\d+\.\d+$/, /^[0-9]+$/, 
                                /^flex$/, /^grid$/, /^block$/, /^inline$/, /^hidden$/, /^visible$/, 
                                /^absolute$/, /^relative$/, /^fixed$/, /^sticky$/, 
                                /^left-\d+$/, /^right-\d+$/, /^top-\d+$/, /^bottom-\d+$/, 
                                /^w-\d+$/, /^h-\d+$/, /^max-w-\d+$/, /^max-h-\d+$/, 
                                /^p-\d+$/, /^m-\d+$/, /^mt-\d+$/, /^mr-\d+$/, /^mb-\d+$/, /^ml-\d+$/, 
                                /^pt-\d+$/, /^pr-\d+$/, /^pb-\d+$/, /^pl-\d+$/, 
                                /^text-\w+$/, /^bg-\w+$/, /^border-\w+$/, /^rounded-\w+$/, 
                                /^lang-\w+$/, /^i18n-\w+$/, /^ltr$/, /^rtl$/, 
                                /^mobile-\w+$/, /^tablet-\w+$/, /^desktop-\w+$/, /^xl-\w+$/, /^sm-\w+$/, /^md-\w+$/, /^lg-\w+$/
                            ];
                            
                            const stableClasses = allClasses.filter(c => {
                                // 过滤掉动态类名
                                const isDynamic = dynamicClassPatterns.some(p => p.test(c));
                                // 过滤掉只有数字或特殊字符的类名
                                const isInvalid = /^[0-9_\-]+$/.test(c);
                                return !isDynamic && !isInvalid;
                            });
                            if (stableClasses.length) {
                                elementSelector += '.' + stableClasses.slice(0, 3).join('.');
                            }
                        }
                    }
                    
                    // 元素类型特定属性处理
                    if (tagName === 'input') {
                        // 对于表单输入元素，添加更多识别属性
                        const type = element.type;
                        elementSelector += `[type="${type}"]`;
                        
                        // 添加name或placeholder属性
                        if (element.name && element.name.length > 0) {
                            elementSelector += `[name="${element.name}"]`;
                        } else if (element.placeholder && element.placeholder.length > 0) {
                            elementSelector += `[placeholder="${element.placeholder}"]`;
                        }
                    } else if (tagName === 'textarea' || tagName === 'select') {
                        // 对于其他表单元素
                        if (element.name && element.name.length > 0) {
                            elementSelector += `[name="${element.name}"]`;
                        } else if (element.placeholder && element.placeholder.length > 0) {
                            elementSelector += `[placeholder="${element.placeholder}"]`;
                        } else if (element.title && element.title.length > 0) {
                            elementSelector += `[title="${element.title}"]`;
                        }
                    } else if (tagName === 'img') {
                        // 对于图片，使用更精确的定位
                        if (element.alt && element.alt.length > 0) {
                            elementSelector += `[alt="${element.alt}"]`;
                        } else if (element.src && element.src.length > 0) {
                            // 对于图片，使用部分src路径
                            const srcParts = element.src.split('/');
                            const filename = srcParts[srcParts.length - 1];
                            elementSelector += `[src*="${filename}"]`;
                        }
                    } else if (tagName === 'a') {
                        // 对于链接，使用href属性
                        if (element.href && element.href.length > 0) {
                            const url = element.href;
                            // 只使用相对路径或域名后的路径
                            const path = url.replace(/^https?:\/\//, '').split('/').slice(1).join('/');
                            if (path.length > 0) {
                                elementSelector += `[href*="${path}"]`;
                            }
                        }
                    } else if (tagName === 'button') {
                        // 对于按钮，添加更多识别属性
                        if (element.textContent && element.textContent.trim().length > 0) {
                            // 只在没有其他更好的属性时使用文本内容
                            const text = element.textContent.trim();
                            if (text.length < 20 && !elementSelector.includes(':has-text(')) {
                                elementSelector += `:has-text("${text}")`;
                            }
                        } else if (element.title && element.title.length > 0 && !elementSelector.includes('[title=')) {
                            elementSelector += `[title="${element.title}"]`;
                        }
                    }
                    
                    // 添加更多稳定属性作为补充
                    const additionalAttrs = ['data-name', 'role', 'aria-label', 'aria-labelledby'];
                    for (const attr of additionalAttrs) {
                        const value = element.getAttribute(attr);
                        if (value && value.length > 0 && !value.includes(' ') && !elementSelector.includes(`[${attr}=`)) {
                            elementSelector += `[${attr}="${value}"]`;
                        }
                    }
                    
                    // 添加更多稳定属性
                    if (element.title && element.title.length > 0 && !elementSelector.includes('[title=')) {
                        elementSelector += `[title="${element.title}"]`;
                    }
                    
                    const parentPath = generateFullPath(element.parentElement, maxDepth, currentDepth + 1);
                    return [...parentPath, elementSelector];
                }
                
                // 生成完整的CSS选择器
                function generateSelector(element) {
                    if (!element) return '';
                    
                    // 生成完整路径
                    let path = generateFullPath(element);
                    
                    // 如果路径为空，直接返回标签名
                    if (path.length === 0) {
                        return element.tagName.toLowerCase();
                    }
                    
                    // 将路径数组转换为完整的CSS选择器
                    let fullSelector = path.join(' > ');
                    
                    // 检查选择器的唯一性
                    try {
                        const matches = document.querySelectorAll(fullSelector);
                        if (matches.length > 1) {
                            // 如果选择器不唯一，添加nth-of-type作为兜底
                            let uniquePath = [...path];
                            let index = 1;
                            let parent = element.parentElement;
                            
                            // 查找当前元素在父元素中的位置
                            if (parent) {
                                const siblings = Array.from(parent.children).filter(child => child.tagName === element.tagName);
                                index = siblings.indexOf(element) + 1;
                                
                                // 如果有多个同类型的兄弟元素，添加nth-of-type
                                if (siblings.length > 1) {
                                    const lastSelector = uniquePath.pop();
                                    const tagName = element.tagName.toLowerCase();
                                    // 确保我们只给基础标签添加nth-of-type
                                    if (lastSelector.startsWith(tagName + '[') || lastSelector === tagName) {
                                        uniquePath.push(`${lastSelector}:nth-of-type(${index})`);
                                    } else {
                                        uniquePath.push(lastSelector);
                                    }
                                    fullSelector = uniquePath.join(' > ');
                                }
                            }
                        }
                    } catch (e) {
                        // 如果查询失败，使用原始选择器
                        console.error('选择器验证失败:', e);
                    }
                    
                    return fullSelector;
                }
                
                // 点击事件监听 - 使用冒泡阶段避免重复事件
                if (document && document.addEventListener) {
                    document.addEventListener('click', function(e) {
                        const target = e.target;
                        let actualTarget = target;
                        
                        // 处理复合组件（如复选框/单选框）：统一使用最外层可交互元素作为目标
                        function findCompositeComponentRoot(element, componentTypes) {
                            let current = element;
                            while (current && current.tagName !== 'BODY' && current.tagName !== 'HTML') {
                                // 检查当前元素是否包含组件类型关键字
                                const hasComponentType = componentTypes.some(type => 
                                    current.className && current.className.includes(type)
                                );
                                
                                // 检查当前元素是否是label标签
                                const isLabel = current.tagName === 'LABEL';
                                
                                // 检查当前元素是否包含目标input类型
                                const hasTargetInput = componentTypes.some(type => 
                                    current.querySelector(`input[type="${type}"]`)
                                );
                                
                                if (hasComponentType || isLabel || hasTargetInput) {
                                    return current;
                                }
                                
                                current = current.parentElement;
                            }
                            return null;
                        }
                        
                        // 处理input类型的复合组件
                        if (target.tagName === 'INPUT') {
                            if (target.type === 'checkbox' || target.type === 'radio') {
                                // 查找复合组件的根元素
                                const rootElement = findCompositeComponentRoot(target, [target.type]);
                                if (rootElement) {
                                    actualTarget = rootElement;
                                }
                            }
                        }
                        // 处理非input类型的复合组件点击
                        else {
                            // 检查是否点击了复选框或单选框的关联元素
                            const checkbox = target.querySelector('input[type="checkbox"]');
                            const radio = target.querySelector('input[type="radio"]');
                            
                            if (checkbox || radio) {
                                // 当前元素包含input，使用当前元素作为目标
                                actualTarget = target;
                            } else {
                                // 检查父元素是否包含checkbox或radio
                                const hasCheckbox = target.closest('[class*="checkbox"]');
                                const hasRadio = target.closest('[class*="radio"]');
                                
                                if (hasCheckbox || hasRadio) {
                                    // 使用closest方法找到最近的包含checkbox或radio类名的元素
                                    actualTarget = hasCheckbox || hasRadio;
                                } else {
                                    // 查找包含checkbox或radio input的父元素
                                    const parentCheckbox = target.closest(':has(input[type="checkbox"])');
                                    const parentRadio = target.closest(':has(input[type="radio"])');
                                    
                                    if (parentCheckbox || parentRadio) {
                                        actualTarget = parentCheckbox || parentRadio;
                                    }
                                }
                            }
                        }
                        
                        const selector = generateSelector(actualTarget);
                        
                        // 记录详细的元素信息
                        const elementInfo = {
                            tagName: actualTarget.tagName,
                            id: actualTarget.id || '',
                            className: actualTarget.className || '',
                            textContent: actualTarget.textContent ? actualTarget.textContent.substring(0, 50) : '',
                            attributes: {}
                        };
                        
                        // 收集重要属性
                        ['name', 'type', 'placeholder', 'value', 'href', 'title', 'alt', 'role', 'data-testid', 'data-cy'].forEach(attr => {
                            if (actualTarget[attr]) {
                                elementInfo.attributes[attr] = actualTarget[attr];
                            }
                        });
                        
                        if (window && window.automationEvents) {
                            window.automationEvents.push({
                                action: 'click',
                                selector: selector,
                                timestamp: Date.now(),
                                elementInfo: elementInfo
                            });
                        }
                    }, false); // 使用冒泡阶段，避免重复捕获
                }
                
                // 输入事件监听 - 带防抖以避免过于频繁的事件
                if (document && document.addEventListener && window && window.automationConfig) {
                    document.addEventListener('input', function(e) {
                        const target = e.target;
                        
                        // 精确检查元素类型，只处理真正可输入的文本元素
                        const isTextInput = (
                            (target.tagName === 'INPUT' && 
                             ['text', 'email', 'password', 'number', 'search', 'url', 'tel'].includes(target.type)) ||
                            target.tagName === 'TEXTAREA' ||
                            (target.tagName === 'INPUT' && !target.type) || // 没有type属性默认为text
                            target.isContentEditable
                        );
                        
                        // 显式排除所有非文本输入类型
                        const isExcludedType = (
                            target.tagName === 'INPUT' && 
                            ['checkbox', 'radio', 'button', 'submit', 'reset', 'file', 'image', 'hidden'].includes(target.type)
                        );
                        
                        if (!isTextInput || isExcludedType) {
                            return; // 忽略非文本输入事件
                        }
                        
                        // 只处理文本输入类型
                        const selector = generateSelector(target);
                        const elementId = selector + '_' + target.tagName; // 创建唯一ID用于防抖
                        
                        // 清除之前的防抖定时器
                        if (window.automationConfig.inputDebounce[elementId]) {
                            clearTimeout(window.automationConfig.inputDebounce[elementId]);
                        }
                        
                        // 设置新的防抖定时器
                        window.automationConfig.inputDebounce[elementId] = setTimeout(() => {
                            if (window && window.automationEvents) {
                                window.automationEvents.push({
                                    action: 'fill',
                                    selector: selector,
                                    text: target.value,
                                    timestamp: Date.now(),
                                    elementInfo: {
                                        tagName: target.tagName,
                                        id: target.id || '',
                                        className: target.className || '',
                                        name: target.name || '',
                                        type: target.type || ''
                                    }
                                });
                            }
                            delete window.automationConfig.inputDebounce[elementId];
                        }, window.automationConfig.debounceDelay);
                    }, true);
                }
                
                // 表单提交事件
                if (document && document.addEventListener) {
                    document.addEventListener('submit', function(e) {
                        const target = e.target;
                        if (target.tagName === 'FORM') {
                            const selector = generateSelector(target);
                            if (window && window.automationEvents) {
                                window.automationEvents.push({
                                    action: 'submit',
                                    selector: selector,
                                    timestamp: Date.now(),
                                    elementInfo: {
                                        tagName: target.tagName,
                                        id: target.id || '',
                                        className: target.className || '',
                                        action: target.action || ''
                                    }
                                });
                            }
                        }
                    }, true);
                }
                
                // 监听页面导航事件
                const originalPushState = history.pushState;
                const originalReplaceState = history.replaceState;
                
                history.pushState = function() {
                    const result = originalPushState.apply(history, arguments);
                    window.automationEvents.push({
                        action: 'navigate',
                        url: location.href,
                        timestamp: Date.now(),
                        navigationType: 'pushState'
                    });
                    return result;
                };
                
                history.replaceState = function() {
                    const result = originalReplaceState.apply(history, arguments);
                    window.automationEvents.push({
                        action: 'navigate',
                        url: location.href,
                        timestamp: Date.now(),
                        navigationType: 'replaceState'
                    });
                    return result;
                };
                
                // 监听hashchange事件
                if (window && window.addEventListener) {
                    window.addEventListener('hashchange', function(e) {
                        if (window && window.automationEvents) {
                            window.automationEvents.push({
                                action: 'navigate',
                                url: location.href,
                                timestamp: Date.now(),
                                navigationType: 'hashchange',
                                oldURL: e.oldURL,
                                newURL: e.newURL
                            });
                        }
                    });
                }
                
                // 监听popstate事件（浏览器前进/后退）
                if (window && window.addEventListener) {
                    window.addEventListener('popstate', function(e) {
                        if (window && window.automationEvents) {
                            window.automationEvents.push({
                                action: 'navigate',
                                url: location.href,
                                timestamp: Date.now(),
                                navigationType: 'popstate',
                                state: e.state
                            });
                        }
                    });
                }
                
                // 改进的滚动事件监听
                if (window && window.addEventListener && window.automationConfig) {
                    window.addEventListener('scroll', function() {
                        // 清除之前的定时器
                        if (window.automationConfig.scrollTimeout) {
                            clearTimeout(window.automationConfig.scrollTimeout);
                        }
                        
                        // 设置新的定时器
                        window.automationConfig.scrollTimeout = setTimeout(() => {
                            if (window && document && window.automationEvents) {
                                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
                                
                                // 计算滚动距离
                                const deltaX = Math.abs(scrollLeft - window.automationConfig.lastScrollPosition.x);
                                const deltaY = Math.abs(scrollTop - window.automationConfig.lastScrollPosition.y);
                                
                                // 只有当滚动距离超过阈值时才记录
                                if (deltaX >= window.automationConfig.scrollThreshold || deltaY >= window.automationConfig.scrollThreshold) {
                                    window.automationEvents.push({
                                        action: 'scroll',
                                        scrollPosition: {
                                            x: scrollLeft,
                                            y: scrollTop
                                        },
                                        scrollDirection: {
                                            x: scrollLeft > window.automationConfig.lastScrollPosition.x ? 'right' : 
                                                scrollLeft < window.automationConfig.lastScrollPosition.x ? 'left' : 'none',
                                            y: scrollTop > window.automationConfig.lastScrollPosition.y ? 'down' : 
                                                scrollTop < window.automationConfig.lastScrollPosition.y ? 'up' : 'none'
                                        },
                                        scrollDistance: {
                                            x: deltaX,
                                            y: deltaY
                                        },
                                        timestamp: Date.now()
                                    });
                                    
                                    // 更新最后滚动位置
                                    window.automationConfig.lastScrollPosition = { x: scrollLeft, y: scrollTop };
                                }
                            }
                        }, 100);
                    });
                }
                
                // 监听键盘事件（可选，用于特殊交互）
                if (document && document.addEventListener) {
                    document.addEventListener('keydown', function(e) {
                        // 只记录特殊按键，如回车、ESC等
                        if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
                            const target = e.target;
                            const selector = generateSelector(target);
                            
                            if (window && window.automationEvents) {
                                window.automationEvents.push({
                                    action: 'keypress',
                                    selector: selector,
                                    key: e.key,
                                    timestamp: Date.now(),
                                    elementInfo: {
                                        tagName: target.tagName,
                                        id: target.id || '',
                                        className: target.className || ''
                                    }
                                });
                            }
                        }
                    }, true);
                }
                
                // 监听悬停事件（可选）
                if (document && document.addEventListener) {
                    document.addEventListener('mouseover', function(e) {
                        const target = e.target;
                        
                        // 只对可交互元素记录悬停
                        const interactiveTags = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA', 'OPTION'];
                        const isInteractive = interactiveTags.includes(target.tagName) || 
                                            target.onclick !== null || 
                                            target.getAttribute('role') === 'button' || 
                                            target.getAttribute('role') === 'link';
                        
                        if (isInteractive) {
                            const selector = generateSelector(target);
                            if (window && window.automationEvents) {
                                window.automationEvents.push({
                                    action: 'hover',
                                    selector: selector,
                                    timestamp: Date.now(),
                                    elementInfo: {
                                        tagName: target.tagName,
                                        id: target.id || '',
                                        className: target.className || ''
                                    }
                                });
                            }
                        }
                    }, true);
                }
                
                console.log('自动化事件监听器已设置完成');
                
                // 设置标志，表示已添加事件监听器
                window.eventListenersAdded = true;
            }
            """;
            
            # 1. 添加初始化脚本，确保新页面加载时自动设置监听器
            await self.page.add_init_script(event_listeners_js);
            
            # 2. 直接在当前页面执行，确保已加载页面也能捕获事件
            await self.page.evaluate(event_listeners_js);
            
            uat_logger.info("事件监听器已成功设置")
        else:
            uat_logger.warning("页面对象为None，无法设置事件监听器")

    async def _on_page_navigated(self, frame):
        """页面导航事件处理函数"""
        # 在页面导航后重新设置事件监听器，确保在新页面上也能记录用户操作
        try:
            # 多层检查确保页面对象有效且可用
            if (self.page is not None and 
                not (hasattr(self.page, 'is_closed') and self.page.is_closed()) and 
                not (hasattr(self.page, 'closed') and self.page.closed)):
                
                try:
                    # 调用统一的事件监听器设置方法
                    # _setup_event_listeners 方法内部会检查 window.eventListenersAdded 标志
                    # 避免重复添加事件监听器
                    await self._setup_event_listeners()
                    uat_logger.info("页面导航完成，已重新设置事件监听器")
                except Exception as inner_e:
                    # 捕获页面操作相关的异常
                    uat_logger.error(f"页面操作失败，可能页面已关闭: {str(inner_e)}")
            else:
                uat_logger.warning("页面对象无效或已关闭，无法设置事件监听器")
        except Exception as e:
            uat_logger.error(f"重新设置页面事件监听器时出错: {str(e)}")

    async def get_recorded_events(self):
        """从浏览器获取记录的事件"""
        if self.page is None:
            uat_logger.warning("页面对象为None，无法获取事件")
            return []
        
        try:
            # 检查页面是否仍然可用
            if hasattr(self.page, 'is_closed') and self.page.is_closed():
                uat_logger.warning("页面已关闭，无法获取事件")
                return []
            
            # 尝试使用更简单的方式检查页面状态
            try:
                # 检查事件数组是否存在
                has_events = await self.page.evaluate("typeof window.automationEvents !== 'undefined'")
                if not has_events:
                    uat_logger.warning("window.automationEvents 未定义，可能是事件监听器未设置")
                    # 尝试重新设置事件监听器
                    await self._setup_event_listeners()
                    return []
                
                # 调试：检查事件数组中是否有内容
                events_count = await self.page.evaluate("window.automationEvents ? window.automationEvents.length : 0")
                
                if events_count == 0:
                    uat_logger.debug("没有获取到浏览器事件")
                    return []
                
                events = await self.page.evaluate("window.automationEvents || []")
                uat_logger.info(f"获取到 {len(events)} 个浏览器事件")
                
                # 清空浏览器端的事件数组
                await self.page.evaluate("window.automationEvents = []")
                return events
            except Exception as e:
                # 页面可能正在导航中，这是正常情况
                uat_logger.debug(f"获取事件时遇到临时错误: {str(e)}")
                return []
        except Exception as e:
            uat_logger.error(f"获取浏览器事件时出错: {str(e)}")
            # 尝试重新设置事件监听器
            try:
                await self._setup_event_listeners()
            except:
                pass
            return []

    async def sync_recorded_events(self):
        """同步浏览器记录的事件到本地"""
        if self.recording and self.page:
            # 检查页面是否仍然可用
            try:
                if hasattr(self.page, 'is_closed') and self.page.is_closed():
                    print("页面已关闭，无法同步事件")
                    return 0
                
                # 检查页面是否仍可访问
                try:
                    # 先尝试访问一个简单的属性来检查页面状态
                    await self.page.title()
                except:
                    print("页面不可访问，无法同步事件")
                    return 0
                
                events = await self.get_recorded_events()
                for event in events:
                    # 将浏览器中的事件转换为录制步骤格式
                    step = {
                        "action": event.get('action'),
                        "timestamp": event.get('timestamp')
                    }
                    
                    if event.get('action') == 'click':
                        step['selector'] = event.get('selector')
                    elif event.get('action') == 'fill':
                        step['selector'] = event.get('selector')
                        step['text'] = event.get('text', '')
                    elif event.get('action') == 'navigate':
                        step['url'] = event.get('url')
                    elif event.get('action') == 'scroll':
                        step['scrollPosition'] = event.get('scrollPosition')
                        step['scrollDirection'] = event.get('scrollDirection')
                        step['scrollDistance'] = event.get('scrollDistance')
                    elif event.get('action') == 'hover':
                        step['selector'] = event.get('selector')
                    elif event.get('action') == 'double_click':
                        step['selector'] = event.get('selector')
                    elif event.get('action') == 'right_click':
                        step['selector'] = event.get('selector')
                    elif event.get('action') == 'submit':
                        step['selector'] = event.get('selector')
                    elif event.get('action') == 'keypress':
                        step['selector'] = event.get('selector')
                        step['key'] = event.get('key')
                    
                    # 去重逻辑：避免添加重复的步骤
                    if self.recorded_steps:
                        last_step = self.recorded_steps[-1]
                        
                        # 检查是否与上一步骤完全相同
                        if last_step['action'] == step['action']:
                            # 计算时间差（毫秒）
                            time_diff = step.get('timestamp', 0) - last_step.get('timestamp', 0)
                            
                            # 对于导航步骤，检查URL是否相同且时间间隔小于2秒
                            if step['action'] == 'navigate' and last_step.get('url') == step.get('url') and time_diff < 2000:
                                continue  # 跳过短时间内重复的导航步骤
                            # 对于点击步骤，检查选择器是否相同且时间间隔小于1秒
                            elif step['action'] == 'click' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                continue  # 跳过短时间内重复的点击步骤
                            # 对于悬停步骤，检查选择器是否相同且时间间隔小于1秒
                            elif step['action'] == 'hover' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                continue  # 跳过短时间内重复的悬停步骤
                            # 对于填充步骤，检查选择器和文本是否相同且时间间隔小于2秒
                            # 填充可能需要更长时间，但短时间内相同内容的填充应跳过
                            elif step['action'] == 'fill' and last_step.get('selector') == step.get('selector') and last_step.get('text') == step.get('text') and time_diff < 2000:
                                continue  # 跳过短时间内重复的填充步骤
                            # 对于按键步骤，检查选择器和按键是否相同且时间间隔小于1秒
                            elif step['action'] == 'keypress' and last_step.get('selector') == step.get('selector') and last_step.get('key') == step.get('key') and time_diff < 1000:
                                continue  # 跳过短时间内重复的按键步骤
                            # 对于提交步骤，检查选择器是否相同且时间间隔小于1秒
                            elif step['action'] == 'submit' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                continue  # 跳过短时间内重复的提交步骤
                            # 对于滚动步骤，检查滚动位置是否基本相同且时间间隔小于1秒
                            elif step['action'] == 'scroll' and last_step.get('scrollPosition') == step.get('scrollPosition') and time_diff < 1000:
                                continue  # 跳过短时间内重复的滚动步骤
                    
                    # 添加到录制步骤中
                    self.recorded_steps.append(step)
                
                return len(events)
            except Exception as e:
                print(f"同步事件时出错: {e}")
                return 0
        return 0
    
    async def navigate_to(self, url: str):
        """导航到指定URL"""
        if self.page is None:
            await self.start_browser()
        
        # 再次检查确保page对象存在
        if self.page is not None:
            # 导航到URL，对于录制时使用domcontentloaded以提高响应速度
            # 但在回放时，我们需要确保页面完全加载
            if self.recording:
                await self.page.goto(url, wait_until='domcontentloaded')
            else:
                # 回放时等待更完整的页面加载状态
                await self.page.goto(url, wait_until='load')
                # 额外等待网络请求完成（对于复杂的单页应用）
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=25000)
                except Exception as e:
                    uat_logger.debug(f"网络idle状态超时(可能是正常的长连接): {str(e)}")
                # 增加JavaScript渲染等待时间，确保动态内容完全显示
                await self.page.wait_for_timeout(1000)
                
                # 等待页面渲染稳定（无更多DOM变化）
                await self.page.evaluate("""
                    () => new Promise(resolve => {
                        let lastScrollHeight = document.body.scrollHeight;
                        let checkCount = 0;
                        const checkInterval = 100;
                        const maxChecks = 10;
                        
                        const checkStability = () => {
                            const currentScrollHeight = document.body.scrollHeight;
                            if (currentScrollHeight === lastScrollHeight) {
                                checkCount++;
                                if (checkCount >= maxChecks) {
                                    resolve();
                                } else {
                                    setTimeout(checkStability, checkInterval);
                                }
                            } else {
                                lastScrollHeight = currentScrollHeight;
                                checkCount = 0;
                                setTimeout(checkStability, checkInterval);
                            }
                        };
                        
                        setTimeout(checkStability, checkInterval);
                    })
                """)
        else:
            uat_logger.error("页面对象为None，无法导航")
            raise Exception("无法创建页面对象")
        self.current_url = url
        
        # 如果正在录制，记录导航步骤，并应用去重逻辑
        if self.recording:
            step = {
                "action": "navigate",
                "url": url,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            
            # 应用去重逻辑
            if self.recorded_steps:
                last_step = self.recorded_steps[-1]
                if last_step['action'] == 'navigate' and last_step.get('url') == step.get('url'):
                    # 计算时间差（毫秒）
                    time_diff = step.get('timestamp', 0) - last_step.get('timestamp', 0)
                    if time_diff < 2000:  # 使用与其他地方一致的2秒阈值
                        return  # 跳过短时间内重复的导航步骤
            
            self.recorded_steps.append(step)
            uat_logger.info(f"录制导航步骤: {url}")
        else:
            uat_logger.info(f"执行导航操作: {url}")
    
    async def click_element(self, selector: str):
        """点击元素"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if self.page is not None:
            element_clicked = False
            try:
                # 等待元素可见且可交互（进一步减少超时时间到2秒，提高执行速度）
                await self.page.wait_for_selector(selector, state='visible', timeout=2000)
                # 使用更健壮的点击方式，尝试不同的点击位置
                await self.page.click(selector, force=True, timeout=2000)
                uat_logger.info(f"成功点击元素: {selector}")
                element_clicked = True
            except Exception as e:
                uat_logger.warning(f"常规点击失败: {str(e)}, 尝试使用JavaScript点击")
                
                # 尝试使用JavaScript点击，先检查元素是否存在
                element_exists = await self.page.evaluate("(selector) => document.querySelector(selector) !== null", selector)
                if element_exists:
                    # 尝试使用JavaScript点击
                    await self.page.evaluate("(selector) => document.querySelector(selector).click();", selector)
                    uat_logger.info(f"使用JavaScript成功点击元素: {selector}")
                    element_clicked = True
                else:
                    uat_logger.error(f"元素不存在，无法使用JavaScript点击: {selector}")
                    
            if not element_clicked:
                # 如果两种点击方式都失败，抛出异常
                raise Exception(f"无法点击元素: {selector}")
            
            # 单选框点击后状态验证
            try:
                # 检查是否是单选框相关选择器
                is_radio_selector = False
                if 'radio' in selector.lower() or 'type="radio"' in selector:
                    is_radio_selector = True
                
                # 如果是单选框选择器，验证点击后状态
                if is_radio_selector:
                    # 等待元素状态更新
                    await self.page.wait_for_timeout(100)
                    
                    # 检查单选框是否被选中
                    evaluate_script = '''() => {
                        const element = document.querySelector('%s');
                        if (element && element.tagName === 'INPUT' && element.type === 'radio') {
                            return element.checked;
                        }
                        // 处理复合组件，找到内部的input元素
                        const inputElement = element?.querySelector('input[type="radio"]');
                        return inputElement ? inputElement.checked : false;
                    }''' % selector
                    is_checked = await self.page.evaluate(evaluate_script)
                    
                    if is_checked:
                        uat_logger.info(f"✅ 单选框点击验证通过: {selector} 已选中")
                    else:
                        uat_logger.warning(f"⚠️ 单选框点击验证警告: {selector} 未选中")
            except Exception as e:
                uat_logger.warning(f"验证单选框状态时出错: {str(e)}")
        
        # 如果正在录制，记录点击步骤
        if self.recording:
            step = {
                "action": "click",
                "selector": selector,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def fill_input(self, selector: str, text: str):
        """填充输入框"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        try:
            # 直接使用Playwright的fill方法，它会自动处理元素查找、可见性和可交互性
            await self.page.fill(selector, text, timeout=3000)
            uat_logger.info(f"成功填充元素: {selector}, 文本: {text}")
            
        except Exception as e:
            uat_logger.error(f"填充元素时出错: {selector}, 错误: {str(e)}")
            # 重新抛出异常，让调用者知道操作失败
            raise
        
        # 如果正在录制，记录填充步骤
        if self.recording:
            step = {
                "action": "fill",
                "selector": selector,
                "text": text,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def scroll_page(self, direction: str = "down", pixels: int = 500):
        """滚动页面"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if direction == "down" and self.page is not None:
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
        elif direction == "up" and self.page is not None:
            await self.page.evaluate(f"window.scrollBy(0, {-pixels})")
        elif direction == "to_top" and self.page is not None:
            await self.page.evaluate("window.scrollTo(0, 0)")
        elif direction == "to_bottom" and self.page is not None:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # 如果正在录制，记录滚动步骤
        if self.recording:
            step = {
                "action": "scroll",
                "direction": direction,
                "pixels": pixels,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def get_page_text(self) -> str:
        """获取页面文本内容"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        text_content = await self.page.inner_text('body')
        return text_content
    
    async def extract_element_text(self, selector: str) -> str:
        """提取特定元素的文本"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        try:
            # 等待元素可见
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            text = await self.page.inner_text(selector)
            return text if text else ""
        except:
            try:
                # 尝试使用text_content
                text = await self.page.text_content(selector)
                return text if text else ""
            except:
                return ""
    
    async def get_element_attributes(self, selector: str) -> Dict[str, str]:
        """获取元素属性"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        attributes = {}
        try:
            # 等待元素可见
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            # 获取元素的所有属性
            attrs = await self.page.evaluate(f"""
                (selector) => {{
                    const element = document.querySelector(selector);
                    if (!element) return {{}};
                    const attrs = {{}};
                    for (let attr of element.attributes) {{
                        attrs[attr.name] = attr.value;
                    }}
                    return attrs;
                }}
            """, selector)
            return attrs
        except:
            return {}
    
    async def get_all_links(self) -> List[Dict[str, str]]:
        """获取页面上所有链接"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        links = await self.page.evaluate("""
            () => {
                const elements = document.querySelectorAll('a[href]');
                return Array.from(elements).map(el => ({
                    text: el.textContent.trim(),
                    href: el.href,
                    title: el.title
                }));
            }
        """)
        return links
    
    async def extract_element_data(self, selector: str) -> Dict[str, Any]:
        """提取元素的各种数据"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        try:
            # 直接尝试获取元素数据，不等待元素可见
            # 移除元素加载限制，允许在页面加载过程中进行录制
            data = await self.page.evaluate(f"""
                (selector) => {{
                    const element = document.querySelector(selector);
                    if (!element) return {{}};
                    
                    return {{
                        textContent: element.textContent ? element.textContent.trim() : '',
                        innerHTML: element.innerHTML ? element.innerHTML.trim() : '',
                        attributes: {{
                            id: element.id,
                            className: element.className,
                            tagName: element.tagName,
                            href: element.href,
                            src: element.src,
                            alt: element.alt,
                            title: element.title,
                            value: element.value,
                            placeholder: element.placeholder,
                            type: element.type,
                            name: element.name,
                            ...element.dataset  // data-* 属性
                        }},
                        styles: {{
                            display: getComputedStyle(element).display,
                            visibility: getComputedStyle(element).visibility,
                            opacity: getComputedStyle(element).opacity,
                        }},
                        rect: element.getBoundingClientRect ? {{
                            x: element.getBoundingClientRect().x,
                            y: element.getBoundingClientRect().y,
                            width: element.getBoundingClientRect().width,
                            height: element.getBoundingClientRect().height,
                            top: element.getBoundingClientRect().top,
                            right: element.getBoundingClientRect().right,
                            bottom: element.getBoundingClientRect().bottom,
                            left: element.getBoundingClientRect().left
                        }} : null,
                        isVisible: element.offsetParent !== null,
                        isEnabled: element.disabled !== true,
                        isSelected: element.selected || element.checked || false
                    }};
                }}
            """, selector)
            
            return data
        except Exception as e:
            print(f"提取元素数据时出错: {e}")
            return {}
    
    async def get_page_data(self) -> Dict[str, Any]:
        """获取页面的全面数据"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        page_data = await self.page.evaluate("""
            () => {
                return {
                    url: window.location.href,
                    title: document.title,
                    textContent: document.body ? document.body.textContent.trim() : '',
                    html: document.documentElement.outerHTML,
                    metaTags: Array.from(document.querySelectorAll('meta')).map(meta => ({
                        name: meta.name,
                        property: meta.property,
                        content: meta.content
                    })),
                    links: Array.from(document.querySelectorAll('a[href]')).length,
                    images: Array.from(document.querySelectorAll('img')).length,
                    forms: Array.from(document.querySelectorAll('form')).length,
                    inputs: Array.from(document.querySelectorAll('input, textarea, select')).length,
                    headings: {
                        h1: Array.from(document.querySelectorAll('h1')).map(el => el.textContent.trim()),
                        h2: Array.from(document.querySelectorAll('h2')).map(el => el.textContent.trim()),
                        h3: Array.from(document.querySelectorAll('h3')).map(el => el.textContent.trim()),
                    },
                    scripts: Array.from(document.querySelectorAll('script')).length,
                    stylesheets: Array.from(document.querySelectorAll('link[rel="stylesheet"]')).length
                };
            }
        """)
        
        return page_data
    
    async def analyze_page_content(self, selector: str = 'body') -> Dict[str, Any]:
        """分析页面内容"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        try:
            if selector == 'body':
                text_content = await self.page.inner_text('body')
            else:
                text_content = await self.page.inner_text(selector)
            
            # 分析文本内容
            words = text_content.split()
            word_count = len(words)
            char_count = len(text_content)
            
            # 提取所有链接
            links = await self.get_all_links()
            
            # 提取所有图片
            images = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('img')).map(img => ({
                        src: img.src,
                        alt: img.alt,
                        title: img.title
                    }));
                }
            """)
            
            analysis = {
                'textContent': text_content,
                'wordCount': word_count,
                'charCount': char_count,
                'links': links,
                'images': images,
                'summary': f"页面包含 {word_count} 个词, {len(links)} 个链接, {len(images)} 个图片"
            }
            
            return analysis
        except Exception as e:
            print(f"分析页面内容时出错: {e}")
            return {'error': str(e)}
    
    async def wait_for_element_visible(self, selector: str, timeout: int = 30000):
        """等待元素可见"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except:
            return False
    
    async def hover_element(self, selector: str):
        """悬停在元素上"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        # 悬停步骤通常不是必要的，设置较短的超时时间
        try:
            # 等待元素可见（减少超时时间到2秒）
            await self.page.wait_for_selector(selector, state='visible', timeout=2000)
            # 使用更健壮的悬停方式
            await self.page.hover(selector, timeout=2000)
            uat_logger.info(f"成功悬停元素: {selector}")
        except Exception as e:
            uat_logger.warning(f"悬停失败，这通常不影响执行: {str(e)}")
            # 悬停失败不影响后续操作，不尝试JavaScript模拟
        
        # 如果正在录制，记录悬停步骤
        if self.recording:
            step = {
                "action": "hover",
                "selector": selector,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def double_click_element(self, selector: str):
        """双击元素"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if self.page is not None:
            # 等待元素可见且可交互
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.dblclick(selector)
        
        # 如果正在录制，记录双击步骤
        if self.recording:
            step = {
                "action": "double_click",
                "selector": selector,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def right_click_element(self, selector: str):
        """右键点击元素"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if self.page is not None:
            # 等待元素可见且可交互
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.click(selector, button="right")
        
        # 如果正在录制，记录右键步骤
        if self.recording:
            step = {
                "action": "right_click",
                "selector": selector,
                "timestamp": int(time.time() * 1000)  # 转换为毫秒，与浏览器事件保持一致
            }
            self.recorded_steps.append(step)
    
    async def get_element_screenshot(self, selector: str, path: str = None):
        """截取特定元素的截图"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if path is None:
            path = f"element_screenshot_{int(time.time())}.png"
        
        # 等待元素可见
        await self.page.wait_for_selector(selector, state='visible', timeout=10000)
        await self.page.locator(selector).screenshot(path=path)
        return path
    
    async def get_page_elements(self) -> List[Dict[str, Any]]:
        """获取页面上所有可交互元素的信息"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        elements = await self.page.evaluate("""
            () => {
                const elements = [];
                
                // 获取所有可交互的元素
                const selector = 'button, input, textarea, select, a, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="menuitem"], [role="tab"], [role="option"], [role="listbox"], [role="combobox"], [role="gridcell"], [role="treeitem"], [role="slider"], [role="progressbar"], [role="img"], [role="tooltip"], [role="dialog"], [role="alert"], [role="alertdialog"], [role="application"], [role="banner"], [role="complementary"], [role="contentinfo"], [role="form"], [role="main"], [role="navigation"], [role="region"], [role="search"], [role="status"], [role="tabpanel"], [role="timer"], [role="toolbar"], [role="tooltip"], [role="tree"], [role="treegrid"], [role="grid"], [role="gridcell"], [role="row"], [role="rowgroup"], [role="columnheader"], [role="rowheader"], [role="separator"], [role="presentation"], [role="none"], [tabindex], [onclick], [ondblclick], [onmousedown], [onmouseup], [onmouseover], [onmousemove], [onmouseout], [onkeypress], [onkeydown], [onkeyup], [class*="btn"], [class*="button"], [class*="input"], [class*="select"], [class*="click"], [class*="toggle"], [class*="menu"], [class*="nav"], [class*="link"], [class*="item"], [class*="option"], [class*="control"], [class*="field"], [class*="action"], [class*="trigger"], [id*="btn"], [id*="button"], [id*="input"], [id*="select"], [id*="click"], [id*="toggle"], [id*="menu"], [id*="nav"], [id*="link"], [id*="item"], [id*="option"], [id*="control"], [id*="field"], [id*="action"], [id*="trigger"]';
                
                const elementList = document.querySelectorAll(selector);
                
                for (let i = 0; i < elementList.length; i++) {
                    const el = elementList[i];
                    
                    // 获取元素的可见性
                    const isVisible = el.offsetParent !== null;
                    
                    // 跳过不可见的元素
                    if (!isVisible) continue;
                    
                    // 获取元素的边界框
                    const rect = el.getBoundingClientRect();
                    
                    // 获取各种可能的标识符
                    const id = el.id;
                    const classes = el.className;
                    const tagName = el.tagName.toLowerCase();
                    const textContent = el.textContent ? el.textContent.trim().substring(0, 50) : '';
                    const title = el.title;
                    const ariaLabel = el.getAttribute('aria-label');
                    const placeholder = el.placeholder;
                    const alt = el.alt;
                    
                    // 构建选择器
                    let selector = tagName;
                    if (id) selector += `#${id}`;
                    if (classes) {
                        const classList = classes.split(' ').filter(c => c !== '');
                        for (const cls of classList) {
                            if (cls) selector += `.${cls}`;
                        }
                    }
                    
                    elements.push({
                        selector: selector,
                        tagName: tagName,
                        id: id,
                        classes: classes,
                        textContent: textContent,
                        title: title,
                        ariaLabel: ariaLabel,
                        placeholder: placeholder,
                        alt: alt,
                        rect: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            top: rect.top,
                            right: rect.right,
                            bottom: rect.bottom,
                            left: rect.left
                        },
                        isVisible: isVisible
                    });
                }
                
                return elements;
            }
        """)
        
        return elements
    
    async def get_page_title(self) -> str:
        """获取页面标题"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        return await self.page.title()
    
    async def get_current_url(self) -> str:
        """获取当前URL"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        return self.page.url
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000):
        """等待元素出现"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def get_element_count(self, selector: str) -> int:
        """获取指定选择器的元素数量"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        count = await self.page.evaluate(f"""
            () => {{
                return document.querySelectorAll('{selector}').length;
            }}
        """)
        return count
    
    async def take_screenshot(self, path: str = None):
        """截取页面截图"""
        if self.page is None:
            raise Exception("浏览器未启动")
        
        if path is None:
            path = f"screenshot_{int(time.time())}.png"
        
        await self.page.screenshot(path=path)
        return path
    
    async def execute_script_steps(self, steps: List[Dict[str, Any]]):
        """执行脚本步骤"""
        if self.page is None:
            await self.start_browser(headless=False)
        else:
            # 确保窗口最大化 - 使用与start_browser相同的Windows API策略
            try:
                # 调用Windows API获取真实屏幕尺寸
                user32 = ctypes.windll.user32
                avail_width = user32.GetSystemMetrics(78)  # SM_CXAVAILABLE
                avail_height = user32.GetSystemMetrics(79)  # SM_CYAVAILABLE
                
                uat_logger.info(f"脚本执行时获取的可用工作区尺寸: {avail_width}x{avail_height}")
                
                # 获取当前窗口大小信息用于验证
                viewport_size = await self.page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                uat_logger.info(f"脚本执行时窗口大小: {viewport_size['width']}x{viewport_size['height']}")
            except Exception as e:
                uat_logger.warning(f"获取窗口大小信息时出错: {str(e)}")
        
        # 步骤去重逻辑
        if not steps:
            return []
            
        # 第一阶段：合并所有相同选择器的填充步骤（无论是否连续）
        # 创建一个字典存储每个选择器的最新填充值
        fill_values = {}
        all_steps = []
        
        # 遍历所有步骤，收集填充值和非填充步骤
        for step in steps:
            if step['action'] == 'fill':
                selector = step.get('selector')
                if selector:
                    # 更新该选择器的最新填充值
                    fill_values[selector] = step
                    all_steps.append(step)  # 保留原始填充步骤用于执行顺序
            else:
                all_steps.append(step)
        
        # 第二阶段：合并连续的重复步骤和处理填充步骤
        deduplicated_steps = []
        last_step = None
        
        # 跟踪已处理的填充选择器
        processed_fills = set()
        
        # 跟踪所有已处理的点击步骤（用于处理非连续的重复点击）
        processed_clicks = {}
        
        for step in all_steps:
            # 过滤悬停动作，不记录和执行
            if step['action'] == 'hover':
                uat_logger.info(f"跳过悬停步骤: {step.get('selector')}")
                continue
            
            if step['action'] == 'fill':
                selector = step.get('selector')
                if selector:
                    # 如果该选择器已经处理过，跳过
                    if selector in processed_fills:
                        continue
                    
                    # 获取最新的填充值
                    if selector in fill_values:
                        latest_fill = fill_values[selector]
                        uat_logger.info(f"使用最新填充值: {selector} -> {latest_fill.get('text')}")
                        deduplicated_steps.append(latest_fill)
                        processed_fills.add(selector)
                    continue
            
            # 处理点击步骤 - 特殊处理单选框/复选框的重复点击
            if step['action'] == 'click':
                selector = step.get('selector')
                if selector:
                    # 检测是否为单选框或复选框相关选择器
                    # 更准确的检测方式：基于选择器和元素信息
                    is_radio = False
                    is_checkbox = False
                    
                    # 首先检查选择器中是否包含明确的单选框/复选框标识
                    selector_lower = selector.lower()
                    if 'radio' in selector_lower:
                        is_radio = True
                    elif 'checkbox' in selector_lower:
                        # 注意：有些单选框可能使用checkbox的样式或类名
                        # 对于这种情况，我们也将其视为单选框处理
                        # 因为用户通常不希望单选框被取消选择
                        is_radio = True
                        # is_checkbox = True
                    
                    # 移除动态类名，生成稳定的选择器用于比较
                    import re
                    stable_selector = selector
                    # 移除所有以is-开头的动态类（如is-loading、is-focus、is-active等）
                    stable_selector = re.sub(r'\.(is-\w+)', '', stable_selector)
                    # 移除所有以el-开头的动态类（Element UI临时类名）
                    stable_selector = re.sub(r'\.(el-\w+-\w+)', '', stable_selector)
                    # 移除所有以has-开头的动态类
                    stable_selector = re.sub(r'\.(has-\w+)', '', stable_selector)
                    # 移除连续的空格和重复的>符号
                    stable_selector = re.sub(r'\s+', ' ', stable_selector)
                    stable_selector = re.sub(r'\s*>\s*', ' > ', stable_selector)
                    stable_selector = stable_selector.strip()
                    
                    # 特殊处理：如果选择器只剩下基础元素类型（如span、div），则保留原始选择器的前两个类名
                    if '.' not in stable_selector and selector.count('.') >= 2:
                        # 保留原始选择器的基础元素和前两个类名
                        parts = selector.split(' ')
                        new_parts = []
                        for part in parts:
                            if '.' in part:
                                # 提取元素类型和前两个类名
                                element_class_parts = part.split('.')
                                if len(element_class_parts) > 2:
                                    new_parts.append('.'.join(element_class_parts[:3]))
                                else:
                                    new_parts.append(part)
                            else:
                                new_parts.append(part)
                        stable_selector = ' '.join(new_parts)
                    
                    # 对于单选框：同一选择器的非连续重复点击应该被过滤
                    # 因为单选框点击一次就足够，重复点击会导致状态切换
                    if is_radio:
                        if stable_selector in processed_clicks:
                            uat_logger.info(f"跳过非连续的重复点击步骤（单选框）: {selector}")
                            continue
                        # 记录已处理的单选框点击
                        processed_clicks[stable_selector] = True
                    
                    # 对于复选框：可以多次点击切换状态，所以不应该过滤重复点击
                    # 对于普通元素：也不应该过滤重复点击，因为用户可能需要多次点击
                    elif not is_checkbox:
                        # 记录已处理的点击，但不用于过滤，仅作参考
                        processed_clicks[stable_selector] = True
            
            # 处理其他类型的步骤
            if not last_step:
                deduplicated_steps.append(step)
                last_step = step
                continue
            
            # 跳过连续的重复步骤
            if last_step['action'] == step['action']:
                if step['action'] == 'navigate':
                    if last_step.get('url') == step.get('url'):
                        uat_logger.info(f"跳过重复导航步骤: {step.get('url')}")
                        continue
                elif step['action'] == 'click' or step['action'] == 'hover':
                    if last_step.get('selector') == step.get('selector'):
                        uat_logger.info(f"跳过重复{step['action']}步骤: {step.get('selector')}")
                        continue
                elif step['action'] == 'scroll':
                    if last_step.get('scrollPosition') == step.get('scrollPosition'):
                        uat_logger.info(f"跳过重复滚动步骤")
                        continue
            
            deduplicated_steps.append(step)
            last_step = step
        
        results = []
        for step in deduplicated_steps:
            action = step.get("action")
            try:
                if action == "navigate":
                    url = step.get("url")
                    await self.navigate_to(url)
                    # 确保页面完全加载完成
                    if self.page:
                        uat_logger.info("导航后等待页面完全加载")
                        await self.page.wait_for_load_state('domcontentloaded', timeout=30000)
                        await self.page.wait_for_load_state('load', timeout=30000)
                elif action == "click":
                    selector = step.get("selector")
                    
                    # 尝试点击元素，如果失败则尝试处理动态选择器
                    try:
                        await self.click_element(selector)
                    except Exception as e:
                        # 如果点击失败，检查是否是动态选择器导致的
                        uat_logger.warning(f"点击失败: {str(e)}")
                        # 尝试使用更宽松的选择器（移除动态class）
                        if '.' in selector:
                            # 对于CSS选择器，尝试移除动态类名（如is-loading、is-focus等）
                            import re
                            # 保留基础元素类型和非动态类
                            # 移除所有以is-开头的动态类（如is-loading、is-focus、is-active等）
                            base_selector = re.sub(r'\.(is-\w+)', '', selector)
                            # 移除所有以el-开头的动态类（Element UI临时类名）
                            base_selector = re.sub(r'\.(el-\w+-\w+)', '', base_selector)
                            # 移除所有以has-开头的动态类
                            base_selector = re.sub(r'\.(has-\w+)', '', base_selector)
                            # 移除连续的空格和重复的>符号
                            base_selector = re.sub(r'\s+', ' ', base_selector)
                            base_selector = re.sub(r'\s*>\s*', ' > ', base_selector)
                            base_selector = base_selector.strip()
                            
                            if base_selector != selector:
                                uat_logger.info(f"尝试使用更宽松的选择器: {base_selector}")
                                # 等待基础选择器的元素可见
                                await self.page.wait_for_selector(base_selector, state='visible', timeout=5000)
                                await self.page.click(base_selector, force=True, timeout=5000)
                                uat_logger.info(f"使用宽松选择器成功点击元素: {base_selector}")
                            else:
                                # 如果无法简化选择器，重新抛出异常
                                raise
                    
                    # 检查是否是可能导致页面刷新的点击操作（如提交按钮）
                    if self.page:
                        try:
                            # 等待可能的页面导航完成
                            # 使用wait_for_event监听framenavigated事件，如果在1秒内发生则等待页面加载
                            async def wait_for_navigation():
                                try:
                                    # 1. 首先记录当前URL，用于后续比较是否真正发生导航
                                    current_url = self.page.url
                                    
                                    # 2. 使用较短时间等待导航事件，减少无导航时的延迟
                                    navigation_occurred = False
                                    
                                    try:
                                        # 等待可能的导航事件，减少超时时间到1秒
                                        await self.page.wait_for_event('framenavigated', timeout=1000)
                                        
                                        # 3. 检查URL是否真正发生变化，避免将iframe导航或局部更新误认为页面导航
                                        if self.page.url != current_url:
                                            uat_logger.info(f"检测到页面导航: {current_url} -> {self.page.url}")
                                            navigation_occurred = True
                                        else:
                                            uat_logger.info("URL未变化，忽略局部导航事件")
                                            navigation_occurred = False
                                    except Exception:
                                        # 没有检测到导航，使用简化的等待策略
                                        uat_logger.info("未检测到页面导航，使用简化等待策略")
                                        navigation_occurred = False
                                    
                                    # 4. 只有在真正发生导航时，才执行完整的页面加载等待
                                    if navigation_occurred:
                                        uat_logger.info("等待DOM内容加载完成")
                                        await self.page.wait_for_load_state('domcontentloaded', timeout=30000)
                                        
                                        uat_logger.info("等待页面可见内容加载")
                                        await self.page.wait_for_load_state('load', timeout=30000)
                                        
                                        # 5. 针对复杂页面，增加额外的等待策略
                                        try:
                                            # 等待网络请求基本完成（允许少量长连接）
                                            uat_logger.info("等待网络请求基本完成")
                                            await self.page.wait_for_load_state('networkidle', timeout=25000)
                                        except Exception as e:
                                            uat_logger.debug(f"网络idle状态超时(可能是正常的长连接): {str(e)}")
                                        
                                        # 6. 增加JavaScript渲染等待时间，确保动态内容完全显示
                                        uat_logger.info("等待JavaScript渲染完成")
                                        await self.page.wait_for_timeout(1000)
                                        
                                        # 7. 等待页面渲染稳定（无更多DOM变化）
                                        uat_logger.info("等待页面渲染稳定")
                                        await self.page.evaluate("""
                                            () => new Promise(resolve => {
                                                let lastScrollHeight = document.body.scrollHeight;
                                                let checkCount = 0;
                                                const checkInterval = 100;
                                                const maxChecks = 10;
                                                
                                                const checkStability = () => {
                                                    const currentScrollHeight = document.body.scrollHeight;
                                                    if (currentScrollHeight === lastScrollHeight) {
                                                        checkCount++;
                                                        if (checkCount >= maxChecks) {
                                                            resolve();
                                                        } else {
                                                            setTimeout(checkStability, checkInterval);
                                                        }
                                                    } else {
                                                        lastScrollHeight = currentScrollHeight;
                                                        checkCount = 0;
                                                        setTimeout(checkStability, checkInterval);
                                                    }
                                                };
                                                
                                                setTimeout(checkStability, checkInterval);
                                            })
                                        """)
                                        
                                        uat_logger.info("页面加载处理完成")
                                    else:
                                        # 对于没有导航的点击，根据点击类型调整等待时间
                                        if 'input' in selector or 'textarea' in selector or 'form' in selector:
                                            # 如果是表单元素，等待更长时间确保数据保存
                                            uat_logger.info("表单元素操作，等待数据保存完成")
                                            await self.page.wait_for_timeout(800)
                                        else:
                                            # 其他元素点击，使用较短等待时间
                                            await self.page.wait_for_timeout(300)
                                except Exception as e:
                                    uat_logger.warning(f"等待页面加载时发生异常: {str(e)}")
                                    # 即使发生异常，也继续执行，避免整个回放失败
                                    pass
                            
                            await wait_for_navigation()
                        except Exception as e:
                            uat_logger.warning(f"等待页面导航时出错: {str(e)}")
                elif action == "fill":
                    selector = step.get("selector")
                    text = step.get("text")
                    await self.fill_input(selector, text)
                    # 移除填充后的固定等待
                elif action == "scroll":
                    # 处理新的滚动格式
                    if "scrollPosition" in step:
                        scroll_pos = step.get("scrollPosition", {})
                        # 计算滚动距离和方向
                        current_scroll = {"x": 0, "y": 0}  # 默认值
                        if self.page is not None:
                            current_scroll = await self.page.evaluate("""
                                () => ({
                                    x: window.pageXOffset || document.documentElement.scrollLeft,
                                    y: window.pageYOffset || document.documentElement.scrollTop
                                })
                            """)
                        else:
                            uat_logger.warning("页面对象为None，无法获取滚动位置")
                        
                        delta_x = scroll_pos.get("x", 0) - current_scroll["x"]
                        delta_y = scroll_pos.get("y", 0) - current_scroll["y"]
                        
                        # 执行滚动
                        if self.page is not None:
                            await self.page.evaluate(f"window.scrollBy({delta_x}, {delta_y})")
                    else:
                        # 处理旧的滚动格式
                        direction = step.get("direction", "down")
                        pixels = step.get("pixels", 500)
                        await self.scroll_page(direction, pixels)
                    
                    # 移除滚动后的固定等待
                elif action == "hover":
                    # 悬停步骤通常不是必要的，跳过以提高执行速度
                    uat_logger.info(f"跳过悬停步骤: {step.get('selector')}")
                    # selector = step.get("selector")
                    # await self.hover_element(selector)
                    # await asyncio.sleep(0.2)
                elif action == "double_click":
                    selector = step.get("selector")
                    await self.double_click_element(selector)
                    # 移除双击后的固定等待
                elif action == "right_click":
                    selector = step.get("selector")
                    await self.right_click_element(selector)
                    # 移除右键点击后的固定等待
                elif action == "submit":
                    selector = step.get("selector")
                    await self.page.click(selector)
                    # 移除表单提交后的固定等待，依赖页面加载状态
                elif action == "keypress":
                    selector = step.get("selector")
                    key = step.get("key")
                    if selector:
                        await self.page.click(selector)  # 先点击确保焦点
                    # 如果没有selector，直接发送按键
                    await self.page.keyboard.press(key)
                    # 移除按键后的固定等待
                elif action == "wait":
                    wait_time = step.get("time", 1000)
                    await asyncio.sleep(wait_time / 1000)  # 转换为秒
                elif action == "wait_for_selector":
                    selector = step.get("selector")
                    timeout = step.get("timeout", 30000)
                    if selector:
                        await self.wait_for_selector(selector, timeout)
                elif action == "wait_for_element_visible":
                    selector = step.get("selector")
                    timeout = step.get("timeout", 30000)
                    if selector:
                        await self.wait_for_element_visible(selector, timeout)
                elif action == "screenshot":
                    # 截取页面截图
                    await self.take_screenshot()
                
                results.append({"status": "success", "step": step})
            except Exception as e:
                results.append({"status": "error", "step": step, "error": str(e)})
        
        return results
    
    async def start_recording(self):
        """开始录制"""
        self.recording = True
        self.recorded_steps = []
        
        # 确保页面上有事件监听器来捕获用户操作
        if self.page:
            await self._setup_event_listeners()
            uat_logger.info("录制已开始，事件监听器已设置")
        else:
            uat_logger.warning("页面对象为None，无法设置事件监听器")
        
        # 不启动后台任务，因为这会导致事件循环冲突
        # 我们将在stop_recording时一次性获取所有事件
        uat_logger.info("录制已开始，事件将在停止录制时获取")
    
    def _get_and_process_events(self):
        """获取并处理浏览器中的事件"""
        # 使用线程安全的方式来获取和处理事件
        import asyncio
        import threading
        from queue import Queue
        
        result_queue = Queue()
        
        def get_events():
            async def run_get_events():
                return await self.get_recorded_events()
            
            try:
                # 创建新的事件循环来运行异步操作
                return asyncio.run(run_get_events())
            except Exception as e:
                print(f"获取事件时出错: {e}")
                return []
        
        def run_in_thread():
            try:
                events = get_events()
                result_queue.put(('success', events))
            except Exception as e:
                result_queue.put(('error', e))
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=2)  # 2秒超时
        
        if result_queue.empty():
            print("获取事件超时")
            return 0
        
        status, events = result_queue.get()
        if status == 'error':
            print(f"获取事件时出错: {events}")
            return 0
        else:
            print(f"获取到 {len(events)} 个浏览器事件")
            # 将浏览器中的事件转换为录制步骤格式
            for event in events:
                        step = {
                            "action": event.get('action'),
                            "timestamp": event.get('timestamp')
                        }
                        
                        if event.get('action') == 'click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'fill':
                            step['selector'] = event.get('selector')
                            step['text'] = event.get('text', '')
                        elif event.get('action') == 'navigate':
                            step['url'] = event.get('url')
                        elif event.get('action') == 'scroll':
                            step['scrollPosition'] = event.get('scrollPosition')
                        elif event.get('action') == 'hover':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'double_click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'right_click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'submit':
                            step['selector'] = event.get('selector')
                        
                        # 添加到录制步骤中
                        self.recorded_steps.append(step)
            
            return len(events)
    
    async def _sync_events_periodically(self):
        """定期同步浏览器事件的后台任务"""
        while self.recording:
            try:
                # 检查页面是否仍然可用
                if not self.page or (hasattr(self.page, 'is_closed') and self.page.is_closed()):
                    print("页面已关闭，停止同步事件")
                    break
                await self.sync_recorded_events()
                # 每秒同步一次
                await asyncio.sleep(1)
            except Exception as e:
                print(f"同步事件时出错: {e}")
                # 出错时也等待一秒再继续
                await asyncio.sleep(1)
    
    async def stop_recording(self) -> List[Dict[str, Any]]:
        """停止录制并返回录制的步骤"""
        self.recording = False
        
        # 在关闭浏览器前，先获取浏览器中记录的所有事件
        if self.page:
            try:
                # 检查页面是否仍然可用
                if not hasattr(self.page, 'is_closed') or not self.page.is_closed():
                    # 直接获取浏览器中剩余的所有事件
                    events = await self.get_recorded_events()
                    uat_logger.info(f"停止录制时获取到 {len(events)} 个浏览器事件")
                    
                    # 将浏览器中的事件转换为录制步骤格式
                    for event in events:
                        step = {
                            "action": event.get('action'),
                            "timestamp": event.get('timestamp')
                        }
                        
                        if event.get('action') == 'click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'fill':
                            step['selector'] = event.get('selector')
                            step['text'] = event.get('text', '')
                        elif event.get('action') == 'navigate':
                            step['url'] = event.get('url')
                        elif event.get('action') == 'scroll':
                            step['scrollPosition'] = event.get('scrollPosition')
                        elif event.get('action') == 'hover':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'double_click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'right_click':
                            step['selector'] = event.get('selector')
                        elif event.get('action') == 'submit':
                            step['selector'] = event.get('selector')
                        
                        # 记录事件
                        uat_logger.log_browser_event(event.get('action', 'unknown'), event)
                        
                        # 应用去重逻辑
                        if self.recorded_steps:
                            last_step = self.recorded_steps[-1]
                            
                            # 检查是否与上一步骤完全相同
                            if last_step['action'] == step['action']:
                                # 计算时间差（毫秒）
                                time_diff = step.get('timestamp', 0) - last_step.get('timestamp', 0)
                                
                                # 对于导航步骤，检查URL是否相同且时间间隔小于2秒
                                if step['action'] == 'navigate' and last_step.get('url') == step.get('url') and time_diff < 2000:
                                    continue  # 跳过短时间内重复的导航步骤
                                # 对于点击步骤，检查选择器是否相同且时间间隔小于1秒
                                elif step['action'] == 'click' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                    continue  # 跳过短时间内重复的点击步骤
                                # 对于悬停步骤，检查选择器是否相同且时间间隔小于1秒
                                elif step['action'] == 'hover' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                    continue  # 跳过短时间内重复的悬停步骤
                                # 对于填充步骤，检查选择器和文本是否相同且时间间隔小于2秒
                                elif step['action'] == 'fill' and last_step.get('selector') == step.get('selector') and last_step.get('text') == step.get('text') and time_diff < 2000:
                                    continue  # 跳过短时间内重复的填充步骤
                                # 对于按键步骤，检查选择器和按键是否相同且时间间隔小于1秒
                                elif step['action'] == 'keypress' and last_step.get('selector') == step.get('selector') and last_step.get('key') == step.get('key') and time_diff < 1000:
                                    continue  # 跳过短时间内重复的按键步骤
                                # 对于提交步骤，检查选择器是否相同且时间间隔小于1秒
                                elif step['action'] == 'submit' and last_step.get('selector') == step.get('selector') and time_diff < 1000:
                                    continue  # 跳过短时间内重复的提交步骤
                                # 对于滚动步骤，检查滚动位置是否基本相同且时间间隔小于1秒
                                elif step['action'] == 'scroll' and last_step.get('scrollPosition') == step.get('scrollPosition') and time_diff < 1000:
                                    continue  # 跳过短时间内重复的滚动步骤
                        
                        # 添加到录制步骤中
                        self.recorded_steps.append(step)
            except Exception as e:
                uat_logger.log_exception("stop_recording", e)
        
        return self.recorded_steps
    
    def _get_recorded_events_sync(self):
        """同步获取录制的事件"""
        # 为了避免事件循环冲突，直接返回空列表
        # 实际的事件同步已经在后台任务中完成
        return []
    
    async def close_browser(self):
        """关闭浏览器"""
        # 设置recording为False以停止任何可能的循环
        self.recording = False
        
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass  # 忽略错误
            self.browser = None
            self.page = None
            self.context = None
        
        if hasattr(self, 'playwright') and self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass  # 忽略错误
    
    async def enable_element_selection(self):
        """启用元素选择模式，显示悬浮窗让用户选择页面元素"""
        if self.page is None:
            await self.start_browser()
        
        try:
            # 注入元素选择悬浮窗
            await self.page.evaluate("""
                (() => {
                    // 检查是否已经存在选择器悬浮窗
                    if (document.getElementById('automation-selector-overlay')) {
                        return; // 已经存在，直接返回
                    }
                    
                    // 创建悬浮窗样式
                    const style = document.createElement('style');
                    style.textContent = `
                        #automation-selector-overlay {
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            z-index: 999999;
                            pointer-events: none;
                        }
                        
                        #automation-selector-highlight {
                            position: absolute;
                            border: 2px solid #ff0000;
                            background-color: rgba(255, 0, 0, 0.2);
                            pointer-events: none;
                            z-index: 999998;
                            transition: all 0.1s ease;
                        }
                        
                        #automation-selector-float {
                            position: fixed;
                            top: 20px;
                            right: 20px;
                            background: white;
                            border: 1px solid #ccc;
                            border-radius: 8px;
                            padding: 15px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                            z-index: 1000000;
                            pointer-events: auto;
                            font-family: Arial, sans-serif;
                            max-width: 300px;
                        }
                        
                        #automation-selector-float h3 {
                            margin-top: 0;
                            font-size: 16px;
                            color: #333;
                        }
                        
                        #automation-selector-float p {
                            margin: 10px 0;
                            font-size: 14px;
                            color: #666;
                        }
                        
                        #automation-selector-float .selector-preview {
                            background: #f5f5f5;
                            padding: 8px;
                            border-radius: 4px;
                            font-family: monospace;
                            font-size: 12px;
                            margin: 10px 0;
                            word-break: break-all;
                        }
                        
                        #automation-selector-float .btn {
                            padding: 8px 12px;
                            margin: 5px 5px 0 0;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                            transition: background-color 0.2s;
                        }
                        
                        #automation-selector-float .btn-primary {
                            background: #007bff;
                            color: white;
                        }
                        
                        #automation-selector-float .btn-primary:hover {
                            background: #0056b3;
                        }
                        
                        #automation-selector-float .btn-secondary {
                            background: #6c757d;
                            color: white;
                        }
                        
                        #automation-selector-float .btn-secondary:hover {
                            background: #545b62;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    // 创建高亮元素
                    const highlight = document.createElement('div');
                    highlight.id = 'automation-selector-highlight';
                    document.body.appendChild(highlight);
                    
                    // 创建悬浮窗
                    const floatWindow = document.createElement('div');
                    floatWindow.id = 'automation-selector-float';
                    floatWindow.innerHTML = `
                        <h3>元素选择工具</h3>
                        <p>将鼠标悬停在页面元素上，点击即可选择该元素</p>
                        <div class="selector-preview">选择器将显示在这里</div>
                        <button class="btn btn-primary" id="select-element-btn">选择该元素</button>
                        <button class="btn btn-secondary" id="cancel-selection-btn">取消选择</button>
                    `;
                    document.body.appendChild(floatWindow);
                    
                    // 全局变量
                    window.automationSelection = {
                        selectedElement: null,
                        highlight: highlight,
                        floatWindow: floatWindow,
                        isSelecting: true
                    };
                    
                    // 生成更精确的CSS选择器函数
                    function generateSelector(element, maxDepth = 4, currentDepth = 0) {
                        if (!element || element.tagName === 'HTML' || currentDepth >= maxDepth) {
                            return '';
                        }
                        
                        let elementSelector = '';
                        const tagName = element.tagName.toLowerCase();
                        
                        // 优先使用ID
                        if (element.id) {
                            return `#${element.id}`;
                        }
                        
                        // 优先使用稳定属性
                        const stableAttrs = ['data-testid', 'data-cy', 'data-test', 'data-qa', 'data-automation', 'data-selector', 'data-key', 'data-id', 'data-name', 'name', 'title', 'role'];
                        let hasStableAttr = false;
                        for (const attr of stableAttrs) {
                            const value = element.getAttribute(attr);
                            if (value && value.length > 0 && !value.includes(' ')) {
                                elementSelector = `${tagName}[${attr}="${value}"]`;
                                hasStableAttr = true;
                                break;
                            }
                        }
                        
                        if (!hasStableAttr) {
                            elementSelector = tagName;
                            // 处理类名，过滤掉动态类名
                            if (element.className) {
                                const allClasses = element.className.split(' ').filter(c => c.length > 0);
                                const dynamicClassPatterns = [
                                    /^is-\w+$/, /^has-\w+$/, /^\w+-\w+-(leave|enter|active)$/, 
                                    /^el-\w+(-\w+)*$/, /^ant-\w+(-\w+)*$/, /^t-[a-zA-Z0-9]{8}$/, 
                                    /^weui-\w+(-\w+)*$/, /^layui-\w+(-\w+)*$/, /^\w+-[a-f0-9]{6,16}$/, 
                                    /^ng-\w+$/, /^vue-\w+$/, /^react-\w+$/, /^svelte-\w+$/, 
                                    /^css-\w+$/, /^scss-\w+$/, /^style-\w+$/, /^component-\w+$/, 
                                    /^theme-\w+$/, /^mode-\w+$/, /^state-\w+$/, /^variant-\w+$/, 
                                    /^hover-\w+$/, /^focus-\w+$/, /^active-\w+$/, /^disabled-\w+$/, 
                                    /^selected-\w+$/, /^checked-\w+$/, /^expanded-\w+$/, /^collapsed-\w+$/,
                                    /^\d+-\w+$/, /^\w+-\d+$/,
                                    /^[a-f0-9]{6,}$/
                                ];
                                
                                const stableClasses = allClasses.filter(c => {
                                    // 过滤掉动态类名
                                    const isDynamic = dynamicClassPatterns.some(p => p.test(c));
                                    // 过滤掉只有数字或特殊字符的类名
                                    const isInvalid = /^[0-9_\-]+$/.test(c);
                                    return !isDynamic && !isInvalid;
                                });
                                if (stableClasses.length) {
                                    elementSelector += '.' + stableClasses.slice(0, 3).join('.');
                                }
                            }
                        }
                        
                        // 元素类型特定属性处理
                        if (tagName === 'input') {
                            // 对于表单输入元素，添加更多识别属性
                            const type = element.type;
                            elementSelector += `[type="${type}"]`;
                            
                            // 添加name或placeholder属性
                            if (element.name && element.name.length > 0) {
                                elementSelector += `[name="${element.name}"]`;
                            } else if (element.placeholder && element.placeholder.length > 0) {
                                elementSelector += `[placeholder="${element.placeholder}"]`;
                            }
                        } else if (tagName === 'textarea' || tagName === 'select') {
                            // 对于其他表单元素
                            if (element.name && element.name.length > 0) {
                                elementSelector += `[name="${element.name}"]`;
                            } else if (element.placeholder && element.placeholder.length > 0) {
                                elementSelector += `[placeholder="${element.placeholder}"]`;
                            } else if (element.title && element.title.length > 0) {
                                elementSelector += `[title="${element.title}"]`;
                            }
                        } else if (tagName === 'img') {
                            // 对于图片，使用更精确的定位
                            if (element.alt && element.alt.length > 0) {
                                elementSelector += `[alt="${element.alt}"]`;
                            } else if (element.src && element.src.length > 0) {
                                // 只使用src的文件名部分
                                const filename = element.src.split('/').pop();
                                elementSelector += `[src*="${filename}"]`;
                            }
                        } else if (tagName === 'a') {
                            // 对于链接，使用href或text
                            if (element.href && element.href.length > 0) {
                                // 只使用href的路径部分
                                const url = new URL(element.href);
                                elementSelector += `[href*="${url.pathname}"]`;
                            } else if (element.textContent && element.textContent.trim().length > 0) {
                                elementSelector += `:contains("${element.textContent.trim().substring(0, 20)}")`;
                            }
                        }
                        
                        // 如果选择器还是太简单，添加父元素选择器
                        if (elementSelector === tagName || elementSelector.startsWith(tagName + '.')) {
                            const parentSelector = generateSelector(element.parentElement, maxDepth, currentDepth + 1);
                            if (parentSelector) {
                                return `${parentSelector} > ${elementSelector}`;
                            }
                        }
                        
                        return elementSelector;
                    }

                    // 元素选择逻辑
                    document.addEventListener('mouseover', function(e) {
                        if (!window.automationSelection.isSelecting) return;
                        
                        const target = e.target;
                        const rect = target.getBoundingClientRect();
                        
                        // 更新高亮框位置和大小
                        window.automationSelection.highlight.style.left = `${rect.left}px`;
                        window.automationSelection.highlight.style.top = `${rect.top}px`;
                        window.automationSelection.highlight.style.width = `${rect.width}px`;
                        window.automationSelection.highlight.style.height = `${rect.height}px`;
                        
                        // 更新选中元素
                        window.automationSelection.selectedElement = target;
                        
                        // 生成选择器并显示
                        const selector = generateSelector(target);
                        const selectorPreview = floatWindow.querySelector('.selector-preview');
                        selectorPreview.textContent = selector;
                    });
                    
                    // 点击元素选择
                    document.addEventListener('click', function(e) {
                        if (!window.automationSelection.isSelecting) return;
                        
                        const target = e.target;
                        if (target === floatWindow || floatWindow.contains(target)) {
                            return; // 点击的是悬浮窗内部，不处理
                        }
                        
                        // 阻止默认事件和冒泡，防止页面跳转等行为
                        e.preventDefault();
                        e.stopPropagation();
                        
                        window.automationSelection.selectedElement = target;
                        const selector = generateSelector(target);
                        const selectorPreview = floatWindow.querySelector('.selector-preview');
                        selectorPreview.textContent = selector;
                    });
                    
                    // 选择按钮事件
                    document.getElementById('select-element-btn').addEventListener('click', function() {
                        if (window.automationSelection.selectedElement) {
                            const element = window.automationSelection.selectedElement;
                            const selector = generateSelector(element);
                            
                            // 触发自定义事件，通知外部代码
                            const event = new CustomEvent('elementSelected', {
                                detail: {
                                    selector: selector,
                                    elementInfo: {
                                        tagName: element.tagName,
                                        id: element.id || '',
                                        className: element.className || '',
                                        textContent: element.textContent ? element.textContent.substring(0, 100) : '',
                                        attributes: {
                                            type: element.type || '',
                                            name: element.name || '',
                                            value: element.value || '',
                                            href: element.href || '',
                                            src: element.src || '',
                                            alt: element.alt || '',
                                            title: element.title || ''
                                        }
                                    }
                                }
                            });
                            window.dispatchEvent(event);
                            
                            // 选择完成后禁用选择模式
                            window.automationSelection.isSelecting = false;
                            window.automationSelection.highlight.style.display = 'none';
                            window.automationSelection.floatWindow.style.display = 'none';
                        }
                    });
                    
                    // 确保generateSelector函数在全局可用，用于get_selected_element方法
                    window.generateSelector = generateSelector;
                    
                    // 取消按钮事件
                    document.getElementById('cancel-selection-btn').addEventListener('click', function() {
                        disableElementSelection();
                    });
                    
                    // 禁用元素选择的函数
                    window.disableElementSelection = function() {
                        // 移除事件监听器（简化处理，实际生产环境中应保存监听器引用以便移除）
                        window.automationSelection.isSelecting = false;
                        
                        // 隐藏高亮和悬浮窗
                        window.automationSelection.highlight.style.display = 'none';
                        window.automationSelection.floatWindow.style.display = 'none';
                    };
                })
            """)
            
            uat_logger.info("元素选择模式已启用")
            return True
        except Exception as e:
            uat_logger.error(f"启用元素选择模式时出错: {str(e)}")
            raise Exception(f"启用元素选择模式失败: {str(e)}")
    
    async def disable_element_selection(self):
        """禁用元素选择模式"""
        if self.page is None:
            return False
        
        try:
            await self.page.evaluate("""
                (() => {
                    if (typeof disableElementSelection === 'function') {
                        disableElementSelection();
                    }
                })
            """)
            
            uat_logger.info("元素选择模式已禁用")
            return True
        except Exception as e:
            uat_logger.error(f"禁用元素选择模式时出错: {str(e)}")
            return False
    
    async def get_selected_element(self):
        """获取用户选择的元素信息"""
        if self.page is None:
            return None
        
        try:
            # 等待元素选择事件
            element_info = await self.page.evaluate("""
                (() => {
                    return new Promise((resolve) => {
                        // 检查是否已经有选中的元素
                        if (window.automationSelection && window.automationSelection.selectedElement) {
                            const element = window.automationSelection.selectedElement;
                            const selector = generateSelector(element);
                            resolve({
                                selector: selector,
                                elementInfo: {
                                    tagName: element.tagName,
                                    id: element.id || '',
                                    className: element.className || '',
                                    textContent: element.textContent ? element.textContent.substring(0, 100) : '',
                                    attributes: {
                                        type: element.type || '',
                                        name: element.name || '',
                                        value: element.value || '',
                                        href: element.href || '',
                                        src: element.src || '',
                                        alt: element.alt || '',
                                        title: element.title || ''
                                    }
                                }
                            });
                        } else {
                            // 监听元素选择事件
                            window.addEventListener('elementSelected', function handler(e) {
                                window.removeEventListener('elementSelected', handler);
                                resolve(e.detail);
                            });
                        }
                    });
                })
            """)
            
            return element_info
        except Exception as e:
            uat_logger.error(f"获取选中元素信息时出错: {str(e)}")
            raise Exception(f"获取选中元素信息失败: {str(e)}")

# 全局实例
automation = PlaywrightAutomation()

# 添加一个函数来重置自动化实例，确保每次录制都是干净的开始
def reset_automation_instance():
    """重置自动化实例，确保干净的状态"""
    global automation
    # 关闭当前实例的浏览器
    try:
        if automation.browser:
            automation.close_browser()
    except:
        pass  # 忽略错误
    
    # 创建新的实例
    automation = PlaywrightAutomation()
    return automation

# 同步包装器函数
# 使用一个全局事件循环来避免重复创建
import threading
import queue

# 创建一个专门的线程池来处理Playwright操作
class PlaywrightWorker:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_thread = None
        self.loop = None
        self.running = False
        self._start_worker()
    
    def _start_worker(self):
        """启动工作线程"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        # 等待线程完全启动
        time.sleep(0.1)
    
    def _worker_loop(self):
        """工作线程的主循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        while self.running:
            try:
                # 获取任务，超时1秒
                task = self.task_queue.get(timeout=1)
                task_id, func, args, kwargs = task
                
                try:
                    # 检查是否是协程函数
                    if asyncio.iscoroutinefunction(func):
                        # 在事件循环中执行异步函数
                        result = self.loop.run_until_complete(func(*args, **kwargs))
                    else:
                        # 执行同步函数
                        result = func(*args, **kwargs)
                    
                    self.result_queue.put((task_id, "success", result))
                except Exception as e:
                    # 获取完整的异常信息
                    import traceback
                    exc_info = traceback.format_exc()
                    self.result_queue.put((task_id, "error", {"message": str(e), "traceback": exc_info}))
                
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                import traceback
                exc_info = traceback.format_exc()
                print(f"工作线程错误: {e}\n{exc_info}")
    
    def execute(self, func, *args, **kwargs):
        """在工作线程中执行函数"""
        # 确保工作线程已启动
        if not self.running or self.worker_thread is None or not self.worker_thread.is_alive():
            self._start_worker()
        
        task_id = str(time.time()) + str(id(func))
        self.task_queue.put((task_id, func, args, kwargs))
        
        # 等待结果
        while True:
            try:
                # 增加超时时间到10分钟（600秒），以支持长脚本执行
                tid, status, result = self.result_queue.get(timeout=600)
                if tid == task_id:
                    if status == "success":
                        return result
                    else:
                        # 处理错误结果
                        if isinstance(result, dict) and "message" in result:
                            raise Exception(result["message"])
                        else:
                            raise Exception(result)
            except queue.Empty:
                raise Exception("执行超时")
    
    def stop(self):
        """停止工作线程"""
        self.running = False
        if hasattr(self, 'worker_thread') and self.worker_thread:
            self.worker_thread.join(timeout=2)
            
        # 清理事件循环
        if hasattr(self, 'loop') and self.loop and not self.loop.is_closed():
            self.loop.close()

# 创建全局工作线程实例
worker = PlaywrightWorker()

def sync_start_browser(headless=False):
    async def run():
        return await automation.start_browser(headless)
    return worker.execute(run)

def sync_navigate_to(url: str):
    async def run():
        return await automation.navigate_to(url)
    return worker.execute(run)

def sync_click_element(selector: str):
    async def run():
        return await automation.click_element(selector)
    return worker.execute(run)

def sync_fill_input(selector: str, text: str):
    async def run():
        return await automation.fill_input(selector, text)
    return worker.execute(run)

def sync_scroll_page(direction: str = "down", pixels: int = 500):
    async def run():
        return await automation.scroll_page(direction, pixels)
    return worker.execute(run)

def sync_get_page_text():
    async def run():
        return await automation.get_page_text()
    return worker.execute(run)

def sync_extract_element_text(selector: str):
    async def run():
        return await automation.extract_element_text(selector)
    return worker.execute(run)

def sync_execute_script_steps(steps: List[Dict[str, Any]]):
    async def run():
        return await automation.execute_script_steps(steps)
    return worker.execute(run)

def sync_close_browser():
    async def run():
        return await automation.close_browser()
    return worker.execute(run)

def sync_get_all_links():
    async def run():
        return await automation.get_all_links()
    return worker.execute(run)

def sync_get_page_title():
    async def run():
        return await automation.get_page_title()
    return worker.execute(run)

def sync_get_current_url():
    async def run():
        return await automation.get_current_url()
    return worker.execute(run)

def sync_wait_for_selector(selector: str, timeout: int = 30000):
    async def run():
        if selector is None:
            raise ValueError("选择器不能为None")
        return await automation.wait_for_selector(selector, timeout)
    return worker.execute(run)

def sync_get_element_count(selector: str):
    async def run():
        return await automation.get_element_count(selector)
    return worker.execute(run)

def sync_take_screenshot(path: str = None):
    async def run():
        return await automation.take_screenshot(path)
    return worker.execute(run)

def sync_hover_element(selector: str):
    async def run():
        return await automation.hover_element(selector)
    return worker.execute(run)

def sync_double_click_element(selector: str):
    async def run():
        return await automation.double_click_element(selector)
    return worker.execute(run)

def sync_right_click_element(selector: str):
    async def run():
        return await automation.right_click_element(selector)
    return worker.execute(run)

def sync_get_page_elements():
    async def run():
        return await automation.get_page_elements()
    return worker.execute(run)

def sync_extract_element_data(selector: str):
    async def run():
        return await automation.extract_element_data(selector)
    return worker.execute(run)

def sync_get_page_data():
    async def run():
        return await automation.get_page_data()
    return worker.execute(run)

def sync_analyze_page_content(selector: str):
    async def run():
        return await automation.analyze_page_content(selector)
    return worker.execute(run)

def sync_wait_for_element_visible(selector: str, timeout: int = 30000):
    async def run():
        if selector is None:
            raise ValueError("选择器不能为None")
        return await automation.wait_for_element_visible(selector, timeout)
    return worker.execute(run)

def sync_start_recording():
    async def run():
        return await automation.start_recording()
    return worker.execute(run)

def sync_stop_recording():
    async def run():
        return await automation.stop_recording()
    return worker.execute(run)

def sync_enable_element_selection():
    async def run():
        return await automation.enable_element_selection()
    return worker.execute(run)

def sync_disable_element_selection():
    async def run():
        return await automation.disable_element_selection()
    return worker.execute(run)

def sync_get_selected_element():
    async def run():
        return await automation.get_selected_element()
    return worker.execute(run)