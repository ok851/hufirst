from flask import Flask, render_template, request, jsonify, session, make_response
from flask_cors import CORS
import os
import time
from database import Database
from playwright_automation import automation, sync_start_browser, sync_navigate_to, sync_scroll_page, sync_get_page_text, sync_extract_element_text, sync_get_page_title, sync_get_current_url, sync_get_all_links, sync_hover_element, sync_double_click_element, sync_right_click_element, sync_click_element, sync_fill_input, sync_get_page_elements, sync_extract_element_data, sync_get_page_data, sync_analyze_page_content, sync_close_browser, sync_execute_script_steps, sync_start_recording, sync_stop_recording, sync_wait_for_selector, sync_wait_for_element_visible, sync_take_screenshot, worker, sync_enable_element_selection, sync_disable_element_selection, sync_get_selected_element  # 使用全局实例和同步包装器
import asyncio
import json
import functools
from logger import uat_logger

# 统一的API错误处理装饰器
def api_error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录异常
            uat_logger.log_exception(f"API Error in {func.__name__}", e)
            # 返回统一的错误响应
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    return wrapper

# API请求日志装饰器
def log_api_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 记录请求，处理没有请求体的情况
        try:
            request_data = request.json if request.method in ['POST', 'PUT', 'PATCH'] else None
        except Exception:
            # 如果解析JSON失败（如请求体为空），使用None
            request_data = None
        uat_logger.log_api_request(func.__name__, request.method, request_data)
        # 执行函数
        response = func(*args, **kwargs)
        # 记录响应
        try:
            if isinstance(response, tuple):
                uat_logger.log_api_response(func.__name__, response[1], response[0].get_json())
            else:
                uat_logger.log_api_response(func.__name__, 200, response.get_json())
        except Exception:
            # 如果响应无法解析为JSON，记录基本信息
            status_code = response[1] if isinstance(response, tuple) else 200
            uat_logger.log_api_response(func.__name__, status_code, None)
        return response
    return wrapper

app = Flask(__name__)
CORS(app)
# 设置Flask应用的密钥，用于session加密
app.secret_key = 'your-secret-key-here'

# 初始化数据库
db = Database()

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 创建测试用例页面
@app.route('/create_case')
def create_case():
    return render_template('create_case.html')

# 录制脚本页面
@app.route('/record_script')
def record_script():
    return render_template('record_script.html')

# 执行脚本页面
@app.route('/playback_script')
def playback_script():
    return render_template('playback_script.html')

# 测试用例列表页面
@app.route('/list_cases')
def list_cases():
    return render_template('list_cases.html')

# 测试脚本列表页面
@app.route('/list_scripts')
def list_scripts():
    return render_template('list_scripts.html')

# 创建测试脚本页面
@app.route('/create_script')
def create_script() -> str:
    return render_template(template_name_or_list='create_script.html')

# API: 创建测试用例
@app.route('/api/create_case', methods=['POST'])
@api_error_handler
@log_api_request
def api_create_case():
    data = request.json
    name = data.get('name', '')
    description = data.get('description', '')
    target_url = data.get('target_url', '')
    
    if not name:
        return jsonify({'error': '用例名称不能为空'}), 400
    
    case_id = db.create_test_case(name, description, target_url)
    return jsonify({'success': True, 'case_id': case_id})

# API: 获取所有测试用例
@app.route('/api/test_cases', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_test_cases():
    cases = db.get_all_test_cases()
    return jsonify({'cases': cases})

# API: 获取单个测试用例
@app.route('/api/test_case/<int:case_id>', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_test_case(case_id):
    case = db.get_test_case(case_id)
    if not case:
        return jsonify({'error': '测试用例不存在'}), 404
    return jsonify({'test_case': case})

# API: 更新测试用例
@app.route('/api/test_case/<int:case_id>', methods=['PUT'])
@api_error_handler
@log_api_request
def api_update_test_case(case_id):
    data = request.json
    name = data.get('name')
    description = data.get('description')
    target_url = data.get('target_url')
    
    success = db.update_test_case(case_id, name, description, target_url)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '更新测试用例失败'}), 400

# API: 删除测试用例
@app.route('/api/test_case/<int:case_id>', methods=['DELETE'])
@api_error_handler
@log_api_request
def api_delete_test_case(case_id):
    success = db.delete_test_case(case_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '删除测试用例失败'}), 400

# API: 创建测试脚本
@app.route('/api/create_script', methods=['POST'])
@api_error_handler
@log_api_request
def api_create_script():
    data = request.json
    case_id = data.get('case_id')
    name = data.get('name', '')
    
    if not case_id or not name:
        return jsonify({'error': '缺少必要参数'}), 400
    
    script_id = db.create_test_script(case_id, name)
    return jsonify({'success': True, 'script_id': script_id})

# API: 获取用例下的所有脚本
@app.route('/api/case/<int:case_id>/scripts', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_case_scripts(case_id):
    scripts = db.get_scripts_by_case(case_id)
    return jsonify({'scripts': scripts})

# API: 获取脚本详情
@app.route('/api/script/<int:script_id>', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_script(script_id):
    script = db.get_test_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404
    return jsonify({'script': script})

# API: 获取所有测试脚本
@app.route('/api/scripts', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_all_scripts():
    scripts = db.get_all_test_scripts()
    return jsonify({'scripts': scripts})

# API: 更新脚本步骤
@app.route('/api/script/<int:script_id>/steps', methods=['PUT'])
@api_error_handler
@log_api_request
def api_update_script_steps(script_id):
    data = request.json
    steps = data.get('steps', [])
    
    success = db.update_test_script_steps(script_id, steps)
    if not success:
        return jsonify({'error': '更新脚本失败'}), 400
    
    return jsonify({'success': True})

# API: 更新测试脚本
@app.route('/api/script/<int:script_id>', methods=['PUT'])
@api_error_handler
@log_api_request
def api_update_script(script_id):
    data = request.json
    name = data.get('name')
    case_id = data.get('case_id')
    
    success = db.update_test_script(script_id, name, case_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '更新测试脚本失败'}), 400

# API: 删除测试脚本
@app.route('/api/script/<int:script_id>', methods=['DELETE'])
@api_error_handler
@log_api_request
def api_delete_script(script_id):
    success = db.delete_test_script(script_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '删除测试脚本失败'}), 400

# API: 启动浏览器进行录制
@app.route('/api/start_recording', methods=['POST'])
@api_error_handler
@log_api_request
def api_start_recording():
    data = request.json or {}
    url = data.get('url', '')
    
    try:
        # 启动浏览器
        uat_logger.info("启动浏览器用于录制")
        sync_start_browser(headless=False)
        
        # 开始录制 - 使用同步函数确保浏览器完全初始化
        sync_start_recording()
        
        # 如果提供了URL，导航到该URL并保存到会话中
        if url:
            uat_logger.log_automation_step("navigate", url, "录制开始时导航")
            sync_navigate_to(url)
            # 保存URL到会话中，以便后续使用
            try:
                session['current_url'] = url
            except Exception:
                # 如果session不可用，忽略错误
                pass
        
        response_data = {'success': True, 'message': '浏览器已启动，开始录制'}
        return jsonify(response_data)
    except Exception as e:
        uat_logger.error(f"启动录制失败: {str(e)}")
        # 尝试关闭浏览器，清理资源
        try:
            sync_close_browser()
        except Exception:
            pass
        return jsonify({'success': False, 'error': f'录制启动失败: {str(e)}'}), 500

# API: 停止录制并保存步骤
@app.route('/api/stop_recording', methods=['POST'])
@api_error_handler
@log_api_request
def api_stop_recording():
    # 获取录制的步骤
    steps = sync_stop_recording()
    uat_logger.info(f"停止录制，获取到 {len(steps)} 个步骤")
    
    # 尝试关闭浏览器，但不影响结果返回
    warning_msg = None
    try:
        sync_close_browser()
        uat_logger.info("浏览器已关闭")
    except Exception as close_error:
        warning_msg = f'录制成功但关闭浏览器时出现问题: {str(close_error)}'
        uat_logger.warning(warning_msg)
    
    response_data = {'success': True, 'steps': steps}
    if warning_msg:
        response_data['warning'] = warning_msg
        
    return jsonify(response_data)

# API: 执行脚本
@app.route('/api/execute_script', methods=['POST'])
@api_error_handler
@log_api_request
def api_execute_script():
    data = request.json or {}
    script_id = data.get('script_id')
    
    if not script_id:
        return jsonify({'success': False, 'error': '缺少脚本ID参数'}), 400
    
    # 获取脚本详情
    script = db.get_test_script(script_id)
    if not script:
        return jsonify({'success': False, 'error': '脚本不存在'}), 404
    
    # 检查脚本是否有步骤
    steps = script.get('steps', [])
    if not steps:
        return jsonify({'success': False, 'error': '脚本没有步骤可以执行'}), 400
    
    uat_logger.info(f"开始执行脚本 ID={script_id}, 共 {len(steps)} 个步骤")
    
    # 执行脚本步骤
    results = sync_execute_script_steps(steps)
    
    # 记录执行结果
    uat_logger.log_script_execution(script_id, len(steps), results)
    
    # 尝试关闭浏览器，但不影响结果返回
    try:
        sync_close_browser()
        uat_logger.info("脚本执行完成，浏览器已关闭")
    except Exception as close_error:
        uat_logger.warning(f"关闭浏览器时出错: {close_error}")
    
    response_data = {'success': True, 'results': results}
    return jsonify(response_data)

# API: 导航到指定URL
@app.route('/api/navigate', methods=['POST'])
@api_error_handler
@log_api_request
def api_navigate():
    data = request.json
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'URL不能为空'}), 400
    
    sync_navigate_to(url)
    return jsonify({'success': True})

# API: 执行滚动操作
@app.route('/api/scroll', methods=['POST'])
@api_error_handler
@log_api_request
def api_scroll():
    data = request.json
    direction = data.get('direction', 'down')
    pixels = data.get('pixels', 500)
    
    sync_scroll_page(direction, pixels)
    return jsonify({'success': True})

# API: 提取页面文本
@app.route('/api/extract_text', methods=['POST'])
@api_error_handler
@log_api_request
def api_extract_text():
    data = request.json
    selector = data.get('selector', 'body')
    
    if selector == 'body':
        text = sync_get_page_text()
    else:
        text = sync_extract_element_text(selector)
    return jsonify({'success': True, 'text': text})

# API: 获取页面标题
@app.route('/api/page_title', methods=['GET'])
@api_error_handler
@log_api_request
def api_page_title():
    title = sync_get_page_title()
    return jsonify({'success': True, 'title': title})

# API: 获取当前URL
@app.route('/api/current_url', methods=['GET'])
@api_error_handler
@log_api_request
def api_current_url():
    url = sync_get_current_url()
    return jsonify({'success': True, 'url': url})

# API: 获取页面上所有链接
@app.route('/api/links', methods=['GET'])
@api_error_handler
@log_api_request
def api_links():
    links = sync_get_all_links()
    return jsonify({'success': True, 'links': links})

# API: 提取元素数据
@app.route('/api/extract_element_data', methods=['POST'])
@api_error_handler
@log_api_request
def api_extract_element_data():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    element_data = automation.extract_element_data(selector)
    return jsonify({'success': True, 'data': element_data})

# API: 获取页面数据
@app.route('/api/page_data', methods=['GET'])
@api_error_handler
@log_api_request
def api_page_data():
    page_data = automation.get_page_data()
    return jsonify({'success': True, 'data': page_data})

# API: 分析页面内容
@app.route('/api/analyze_content', methods=['POST'])
@api_error_handler
@log_api_request
def api_analyze_content():
    data = request.json
    selector = data.get('selector', 'body')
    
    analysis = automation.analyze_page_content(selector)
    return jsonify({'success': True, 'analysis': analysis})

# API: 悬停在元素上
@app.route('/api/hover_element', methods=['POST'])
@api_error_handler
@log_api_request
def api_hover_element():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_hover_element(selector)
    return jsonify({'success': True})

# API: 双击元素
@app.route('/api/double_click', methods=['POST'])
@api_error_handler
@log_api_request
def api_double_click():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_double_click_element(selector)
    return jsonify({'success': True})

# API: 点击元素
@app.route('/api/click_element', methods=['POST'])
@api_error_handler
@log_api_request
def api_click_element():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_click_element(selector)
    return jsonify({'success': True})

# API: 填充输入框
@app.route('/api/fill_input', methods=['POST'])
@api_error_handler
@log_api_request
def api_fill_input():
    data = request.json
    selector = data.get('selector', '')
    text = data.get('text', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_fill_input(selector, text)
    return jsonify({'success': True})

# API: 右键点击元素
@app.route('/api/right_click', methods=['POST'])
@api_error_handler
@log_api_request
def api_right_click():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_right_click_element(selector)
    return jsonify({'success': True})

# API: 等待元素出现
@app.route('/api/wait_for_selector', methods=['POST'])
@api_error_handler
@log_api_request
def api_wait_for_selector():
    data = request.json
    selector = data.get('selector', '')
    timeout = data.get('timeout', 30000)
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_wait_for_selector(selector, timeout)
    return jsonify({'success': True})

# API: 等待元素可见
@app.route('/api/wait_for_element_visible', methods=['POST'])
@api_error_handler
@log_api_request
def api_wait_for_element_visible():
    data = request.json
    selector = data.get('selector', '')
    timeout = data.get('timeout', 30000)
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    sync_wait_for_element_visible(selector, timeout)
    return jsonify({'success': True})

# API: 获取页面元素
@app.route('/api/page_elements', methods=['GET'])
@api_error_handler
@log_api_request
def api_page_elements():
    elements = sync_get_page_elements()
    return jsonify({'success': True, 'elements': elements})

# API: 检查是否存在测试用例
@app.route('/api/has_test_cases', methods=['GET'])
@api_error_handler
@log_api_request
def api_has_test_cases():
    cases = db.get_all_test_cases()
    has_cases = len(cases) > 0
    return jsonify({'success': True, 'has_cases': has_cases})

# API: 获取页面截图
@app.route('/api/screenshot', methods=['GET'])
@api_error_handler
@log_api_request
def api_screenshot():
    try:
        import os
        import time
        from flask import send_file
        
        # 生成截图文件名
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(os.getcwd(), filename)
        
        # 保存截图
        sync_take_screenshot(filepath)
        
        # 返回截图文件
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 启用元素选择模式
@app.route('/api/enable_element_selection', methods=['POST'])
@api_error_handler
@log_api_request
def api_enable_element_selection():
    try:
        sync_enable_element_selection()
        return jsonify({'success': True, 'message': '元素选择模式已启用'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 禁用元素选择模式
@app.route('/api/disable_element_selection', methods=['POST'])
@api_error_handler
@log_api_request
def api_disable_element_selection():
    try:
        sync_disable_element_selection()
        return jsonify({'success': True, 'message': '元素选择模式已禁用'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取选中的元素信息
@app.route('/api/get_selected_element', methods=['GET'])
@api_error_handler
@log_api_request
def api_get_selected_element():
    try:
        element_info = sync_get_selected_element()
        return jsonify({'success': True, 'element': element_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)