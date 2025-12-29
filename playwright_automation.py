import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional
import json
import time
from logger import uat_logger

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
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=headless)
                # 设置初始窗口大小为1920x1080
                self.context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
                self.page = await self.context.new_page()
                
                # 最大化窗口 - 使用Playwright的API
                await self.page.evaluate("""
                    () => {
                        // 先尝试使用现代浏览器的全屏API
                        if (document.documentElement.requestFullscreen) {
                            document.documentElement.requestFullscreen();
                        }
                        // 然后设置窗口大小为屏幕最大可用尺寸
                        window.moveTo(0, 0);
                        window.resizeTo(screen.availWidth, screen.availHeight);
                        return { width: screen.availWidth, height: screen.availHeight };
                    }
                """)
                
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
            event_listeners_js = """
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
                function generateSelector(element) {
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    let path = element.tagName.toLowerCase();
                    
                    // 优先使用数据属性（最稳定的选择器）
                    if (element.dataset.testid) {
                        path += `[data-testid="${element.dataset.testid}"]`;
                        return path; // 数据属性已经足够唯一，直接返回
                    } else if (element.dataset.cy) {
                        path += `[data-cy="${element.dataset.cy}"]`;
                        return path;
                    } else if (element.dataset.id) {
                        path += `[data-id="${element.dataset.id}"]`;
                        return path;
                    } else if (element.dataset.name) {
                        path += `[data-name="${element.dataset.name}"]`;
                        return path;
                    }
                    
                    // 添加类名（选择有意义的类名，避免随机生成的类名）
                    if (element.className) {
                        const classes = element.className.split(' ')
                            .filter(c => c.length > 0)
                            .filter(c => !c.match(/^el-|^ant-|^v-|^Mui/)) // 过滤掉框架自动生成的类名
                            .filter(c => !c.match(/^[a-f0-9]{8}$/i)); // 过滤掉可能是哈希值的类名
                        
                        if (classes.length > 0) {
                            // 选择最有意义的前3个类名
                            const meaningfulClasses = classes.slice(0, 3);
                            path += '.' + meaningfulClasses.join('.');
                        } else {
                            // 如果没有有意义的类名，使用原始类名
                            const allClasses = element.className.split(' ').filter(c => c.length > 0);
                            if (allClasses.length > 0) {
                                path += '.' + allClasses.join('.');
                            }
                        }
                    }
                    
                    // 为表单元素添加类型和名称属性
                    if (path === 'input' || path.startsWith('input.')) {
                        if (element.type) {
                            path += `[type="${element.type}"]`;
                        }
                        if (element.name && element.name.length > 0) {
                            path += `[name="${element.name}"]`;
                        } else if (element.placeholder && element.placeholder.length > 0) {
                            path += `[placeholder="${element.placeholder}"]`;
                        }
                    }
                    
                    // 特别处理复选框和单选框，使用更稳定的选择器
                    if (element.type === 'checkbox' || element.type === 'radio') {
                        // 检查父元素是否有稳定的标识
                        let parent = element.parentElement;
                        if (parent) {
                            // 如果父元素是label，直接返回label的选择器
                            if (parent.tagName === 'LABEL') {
                                return generateSelector(parent);
                            }
                            // 对于Element UI的checkbox组件，父元素可能是span
                            else if (parent.tagName === 'SPAN') {
                                // 检查span是否有checkbox或radio相关的类名
                                if (parent.className && (parent.className.includes('checkbox') || parent.className.includes('radio'))) {
                                    // 直接返回span的选择器，这是实际可点击的元素
                                    return generateSelector(parent);
                                }
                                // 检查span的父元素是否是label
                                let grandParent = parent.parentElement;
                                if (grandParent && grandParent.tagName === 'LABEL') {
                                    return generateSelector(grandParent);
                                }
                                // 检查span的父元素是否也包含checkbox/radio类名
                                if (grandParent && grandParent.tagName === 'SPAN' && grandParent.className && (grandParent.className.includes('checkbox') || grandParent.className.includes('radio'))) {
                                    return generateSelector(grandParent);
                                }
                            }
                        }
                        // 如果没有找到合适的父元素，仍然返回当前元素的选择器，但添加类型标识
                        path += `[type="${element.type}"]`;
                    }
                    
                    // 只有在绝对必要时才使用nth-of-type（作为最后手段）
                    // 先检查选择器是否已经足够唯一
                    const elementsWithSameSelector = document.querySelectorAll(path);
                    if (elementsWithSameSelector.length > 1) {
                        // 找到父元素
                        let parent = element.parentElement;
                        if (parent && parent.tagName !== 'BODY' && parent.tagName !== 'HTML') {
                            // 生成父元素的选择器
                            const parentSelector = generateSelector(parent);
                            // 组合父元素选择器和当前元素选择器
                            path = `${parentSelector} > ${path}`;
                            
                            // 再次检查唯一性
                            const elementsWithCombinedSelector = document.querySelectorAll(path);
                            if (elementsWithCombinedSelector.length > 1) {
                                // 作为最后手段，使用nth-of-type
                                const siblings = Array.from(parent.children).filter(child => {
                                    // 检查子元素是否匹配当前元素的基本选择器
                                    const childPath = child.tagName.toLowerCase() + (child.className ? '.' + child.className.split(' ').filter(c => c.length > 0).join('.') : '');
                                    return childPath === path.split('>').pop().trim();
                                });
                                const index = siblings.indexOf(element);
                                if (index > -1) {
                                    path += `:nth-of-type(${index + 1})`;
                                }
                            }
                        }
                    }
                    
                    return path;
                }
                
                // 点击事件监听 - 使用冒泡阶段避免重复事件
                if (document && document.addEventListener) {
                    document.addEventListener('click', function(e) {
                        const target = e.target;
                        let actualTarget = target;
                        
                        // 处理复合组件（如复选框/单选框）：统一使用最外层可交互元素作为目标
                        if (target.tagName === 'INPUT' && (target.type === 'checkbox' || target.type === 'radio')) {
                            // 如果直接点击了input元素，找到它的父元素
                            let parent = target.parentElement;
                            while (parent && parent.tagName !== 'BODY' && parent.tagName !== 'HTML') {
                                // 查找包含checkbox/radio类名的父元素
                                if (parent.className && (parent.className.includes('checkbox') || parent.className.includes('radio'))) {
                                    actualTarget = parent;
                                    break;
                                }
                                // 如果父元素是label，使用label作为目标
                                if (parent.tagName === 'LABEL') {
                                    actualTarget = parent;
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                            // 如果没找到合适的父元素，仍然使用input作为目标
                        }
                        // 如果点击的是span，检查是否包含checkbox/radio
                        else if (target.tagName === 'SPAN') {
                            const checkbox = target.querySelector('input[type="checkbox"]');
                            const radio = target.querySelector('input[type="radio"]');
                            if (checkbox || radio) {
                                // 对于包含checkbox/radio的span，使用span作为实际目标
                                actualTarget = target;
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
                    # 不等待页面完全加载，立即设置事件监听器以捕获加载过程中的用户操作
                    # 移除页面加载状态等待，允许在页面加载过程中进行录制
                    
                    # 重置事件监听器状态，确保可以重新添加
                    await self.page.evaluate("window.eventListenersAdded = false;")
                    
                    # 调用统一的事件监听器设置方法
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
            # 导航到URL，只等待DOM加载完成，不等待网络请求完成
            # 这样可以在页面加载过程中就开始录制用户操作
            await self.page.goto(url, wait_until='domcontentloaded')
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
            try:
                # 等待元素可见且可交互（进一步减少超时时间到2秒，提高执行速度）
                await self.page.wait_for_selector(selector, state='visible', timeout=2000)
                # 使用更健壮的点击方式，尝试不同的点击位置
                await self.page.click(selector, force=True, timeout=2000)
                uat_logger.info(f"成功点击元素: {selector}")
            except Exception as e:
                uat_logger.warning(f"常规点击失败: {str(e)}, 尝试使用JavaScript点击")
                # 尝试使用JavaScript点击
                await self.page.evaluate(f"document.querySelector('{selector}')?.click();")
                uat_logger.info(f"使用JavaScript成功点击元素: {selector}")
        
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
            # 快速检查元素是否存在，不等待完全可见
            element_exists = await self.page.evaluate(f"document.querySelector('{selector}') !== null")
            if not element_exists:
                uat_logger.warning(f"元素不存在，跳过填充: {selector}")
                return
            
            # 检查元素是否为可输入元素
            is_input = await self.page.evaluate("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (!element) return false;
                    const tagName = element.tagName.toLowerCase();
                    const inputTypes = ['input', 'textarea', 'select'];
                    const isEditable = element.contentEditable === 'true';
                    
                    // 特别排除checkbox和radio类型的input
                    if (tagName === 'input' && (element.type === 'checkbox' || element.type === 'radio')) {
                        return false;
                    }
                    
                    return inputTypes.includes(tagName) || isEditable;
                }
            """, selector)
            
            if is_input:
                # 对可输入元素执行填充，使用更短的超时时间
                await self.page.fill(selector, text, timeout=2000)
                uat_logger.info(f"成功填充元素: {selector}, 文本: {text}")
            else:
                # 对非输入元素，记录警告并跳过
                uat_logger.warning(f"跳过填充非输入元素: {selector}")
                return  # 直接返回，避免继续执行
        except Exception as e:
            uat_logger.error(f"填充元素时出错: {selector}, 错误: {str(e)}")
            # 不再抛出异常，继续执行下一个步骤
            return
        
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
            # 确保窗口最大化
            try:
                await self.page.evaluate("""
                    () => {
                        // 先尝试使用现代浏览器的全屏API
                        if (document.documentElement.requestFullscreen) {
                            document.documentElement.requestFullscreen();
                        }
                        // 然后设置窗口大小为屏幕最大可用尺寸
                        window.moveTo(0, 0);
                        window.resizeTo(screen.availWidth, screen.availHeight);
                        return { width: screen.availWidth, height: screen.availHeight };
                    }
                """)
                uat_logger.info("脚本执行时已最大化窗口")
            except Exception as e:
                uat_logger.warning(f"尝试最大化窗口时出错: {str(e)}")
        
        # 步骤去重逻辑
        if not steps:
            return []
            
        deduplicated_steps = [steps[0]]
        for step in steps[1:]:
            last_step = deduplicated_steps[-1]
            
            # 检查是否与上一步骤完全相同
            if last_step['action'] == step['action']:
                if step['action'] == 'navigate':
                    # 检查URL是否相同
                    if last_step.get('url') == step.get('url'):
                        uat_logger.info(f"跳过重复导航步骤: {step.get('url')}")
                        continue
                elif step['action'] == 'click' or step['action'] == 'hover':
                    # 检查选择器是否相同
                    if last_step.get('selector') == step.get('selector'):
                        uat_logger.info(f"跳过重复{step['action']}步骤: {step.get('selector')}")
                        continue
                elif step['action'] == 'fill':
                    # 检查选择器和文本是否相同
                    if last_step.get('selector') == step.get('selector') and last_step.get('text') == step.get('text'):
                        uat_logger.info(f"跳过重复填充步骤: {step.get('selector')}")
                        continue
                elif step['action'] == 'scroll':
                    # 检查滚动位置是否相同
                    if last_step.get('scrollPosition') == step.get('scrollPosition'):
                        uat_logger.info(f"跳过重复滚动步骤")
                        continue
            
            # 如果步骤不重复，添加到去重后的列表
            deduplicated_steps.append(step)
        
        results = []
        for step in deduplicated_steps:
            action = step.get("action")
            try:
                if action == "navigate":
                    url = step.get("url")
                    await self.navigate_to(url)
                    # 移除导航后的固定等待，依赖页面加载状态
                elif action == "click":
                    selector = step.get("selector")
                    await self.click_element(selector)
                    # 移除点击后的固定等待，依赖元素状态检查
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

def sync_stop_recording():
    async def run():
        return await automation.stop_recording()
    return worker.execute(run)
