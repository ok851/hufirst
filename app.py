from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import time
from database import Database
from playwright_automation import automation, sync_start_browser, sync_navigate_to, sync_scroll_page, sync_get_page_text, sync_extract_element_text, sync_get_page_title, sync_get_current_url, sync_get_all_links, sync_hover_element, sync_double_click_element, sync_right_click_element, sync_click_element, sync_fill_input, sync_get_page_elements, sync_extract_element_data, sync_get_page_data, sync_analyze_page_content, sync_close_browser, sync_execute_script_steps, sync_stop_recording, sync_wait_for_selector, sync_wait_for_element_visible, sync_take_screenshot, worker  # 使用全局实例和同步包装器
import asyncio
import json
from logger import uat_logger

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
def api_get_test_cases():
    cases = db.get_all_test_cases()
    return jsonify({'cases': cases})

# API: 获取单个测试用例
@app.route('/api/test_case/<int:case_id>', methods=['GET'])
def api_get_test_case(case_id):
    case = db.get_test_case(case_id)
    if not case:
        return jsonify({'error': '测试用例不存在'}), 404
    return jsonify({'test_case': case})

# API: 更新测试用例
@app.route('/api/test_case/<int:case_id>', methods=['PUT'])
def api_update_test_case(case_id):
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        target_url = data.get('target_url')
        
        success = db.update_test_case(case_id, name, description, target_url)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '更新测试用例失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 删除测试用例
@app.route('/api/test_case/<int:case_id>', methods=['DELETE'])
def api_delete_test_case(case_id):
    try:
        success = db.delete_test_case(case_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '删除测试用例失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 创建测试脚本
@app.route('/api/create_script', methods=['POST'])
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
def api_get_case_scripts(case_id):
    scripts = db.get_scripts_by_case(case_id)
    return jsonify({'scripts': scripts})

# API: 获取脚本详情
@app.route('/api/script/<int:script_id>', methods=['GET'])
def api_get_script(script_id):
    script = db.get_test_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404
    return jsonify({'script': script})

# API: 获取所有测试脚本
@app.route('/api/scripts', methods=['GET'])
def api_get_all_scripts():
    try:
        scripts = db.get_all_test_scripts()
        return jsonify({'scripts': scripts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 更新脚本步骤
@app.route('/api/script/<int:script_id>/steps', methods=['PUT'])
def api_update_script_steps(script_id):
    data = request.json
    steps = data.get('steps', [])
    
    success = db.update_test_script_steps(script_id, steps)
    if not success:
        return jsonify({'error': '更新脚本失败'}), 400
    
    return jsonify({'success': True})

# API: 更新测试脚本
@app.route('/api/script/<int:script_id>', methods=['PUT'])
def api_update_script(script_id):
    try:
        data = request.json
        name = data.get('name')
        case_id = data.get('case_id')
        
        success = db.update_test_script(script_id, name, case_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '更新测试脚本失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 删除测试脚本
@app.route('/api/script/<int:script_id>', methods=['DELETE'])
def api_delete_script(script_id):
    try:
        success = db.delete_test_script(script_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '删除测试脚本失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 启动浏览器进行录制
@app.route('/api/start_recording', methods=['POST'])
def api_start_recording():
    try:
        data = request.json or {}
        url = data.get('url', '')
        
        uat_logger.log_api_request('/api/start_recording', 'POST', data)
        
        # 启动浏览器
        uat_logger.info("启动浏览器用于录制")
        sync_start_browser(headless=False)
        
        # 开始录制
        worker.execute(automation.start_recording)
        
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
        uat_logger.log_api_response('/api/start_recording', 200, response_data)
        return jsonify(response_data)
    except Exception as e:
        uat_logger.log_exception("api_start_recording", e)
        error_response = {'success': False, 'error': f'启动录制失败: {str(e)}'}
        uat_logger.log_api_response('/api/start_recording', 500, error_response)
        return jsonify(error_response), 500

# API: 停止录制并保存步骤
@app.route('/api/stop_recording', methods=['POST'])
def api_stop_recording():
    try:
        uat_logger.log_api_request('/api/stop_recording', 'POST')
        
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
            
        uat_logger.log_api_response('/api/stop_recording', 200, {'steps_count': len(steps), 'warning': warning_msg})
        return jsonify(response_data)
    except Exception as e:
        uat_logger.log_exception("api_stop_recording", e)
        error_response = {'success': False, 'error': f'停止录制失败: {str(e)}'}
        uat_logger.log_api_response('/api/stop_recording', 500, error_response)
        return jsonify(error_response), 500

# API: 执行脚本
@app.route('/api/execute_script', methods=['POST'])
def api_execute_script():
    try:
        data = request.json or {}
        script_id = data.get('script_id')
        
        uat_logger.log_api_request('/api/execute_script', 'POST', data)
        
        if not script_id:
            error_response = {'success': False, 'error': '缺少脚本ID参数'}
            uat_logger.log_api_response('/api/execute_script', 400, error_response)
            return jsonify(error_response), 400
        
        # 获取脚本详情
        script = db.get_test_script(script_id)
        if not script:
            error_response = {'success': False, 'error': '脚本不存在'}
            uat_logger.log_api_response('/api/execute_script', 404, error_response)
            return jsonify(error_response), 404
        
        # 检查脚本是否有步骤
        steps = script.get('steps', [])
        if not steps:
            error_response = {'success': False, 'error': '脚本没有步骤可以执行'}
            uat_logger.log_api_response('/api/execute_script', 400, error_response)
            return jsonify(error_response), 400
        
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
        uat_logger.log_api_response('/api/execute_script', 200, {'script_id': script_id, 'steps_count': len(results)})
        return jsonify(response_data)
    except Exception as e:
        uat_logger.log_exception("api_execute_script", e)
        error_response = {'success': False, 'error': f'执行脚本失败: {str(e)}'}
        uat_logger.log_api_response('/api/execute_script', 500, error_response)
        return jsonify(error_response), 500

# API: 导航到指定URL
@app.route('/api/navigate', methods=['POST'])
def api_navigate():
    data = request.json
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'URL不能为空'}), 400
    
    try:
        sync_navigate_to(url)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 执行滚动操作
@app.route('/api/scroll', methods=['POST'])
def api_scroll():
    data = request.json
    direction = data.get('direction', 'down')
    pixels = data.get('pixels', 500)
    
    try:
        sync_scroll_page(direction, pixels)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 提取页面文本
@app.route('/api/extract_text', methods=['POST'])
def api_extract_text():
    data = request.json
    selector = data.get('selector', 'body')
    
    try:
        if selector == 'body':
            text = sync_get_page_text()
        else:
            text = sync_extract_element_text(selector)
        return jsonify({'success': True, 'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取页面标题
@app.route('/api/page_title', methods=['GET'])
def api_page_title():
    try:
        title = sync_get_page_title()
        return jsonify({'success': True, 'title': title})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取当前URL
@app.route('/api/current_url', methods=['GET'])
def api_current_url():
    try:
        url = sync_get_current_url()
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取页面上所有链接
@app.route('/api/links', methods=['GET'])
def api_links():
    try:
        links = sync_get_all_links()
        return jsonify({'success': True, 'links': links})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 提取元素数据
@app.route('/api/extract_element_data', methods=['POST'])
def api_extract_element_data():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        element_data = automation.extract_element_data(selector)
        return jsonify({'success': True, 'data': element_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取页面数据
@app.route('/api/page_data', methods=['GET'])
def api_page_data():
    try:
        page_data = automation.get_page_data()
        return jsonify({'success': True, 'data': page_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 分析页面内容
@app.route('/api/analyze_content', methods=['POST'])
def api_analyze_content():
    data = request.json
    selector = data.get('selector', 'body')
    
    try:
        analysis = automation.analyze_page_content(selector)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 悬停在元素上
@app.route('/api/hover_element', methods=['POST'])
def api_hover_element():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_hover_element(selector)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 双击元素
@app.route('/api/double_click', methods=['POST'])
def api_double_click():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_double_click_element(selector)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 点击元素
@app.route('/api/click_element', methods=['POST'])
def api_click_element():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_click_element(selector)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 填充输入框
@app.route('/api/fill_input', methods=['POST'])
def api_fill_input():
    data = request.json
    selector = data.get('selector', '')
    text = data.get('text', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_fill_input(selector, text)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 右键点击元素
@app.route('/api/right_click', methods=['POST'])
def api_right_click():
    data = request.json
    selector = data.get('selector', '')
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_right_click_element(selector)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 等待元素出现
@app.route('/api/wait_for_selector', methods=['POST'])
def api_wait_for_selector():
    data = request.json
    selector = data.get('selector', '')
    timeout = data.get('timeout', 30000)
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_wait_for_selector(selector, timeout)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 等待元素可见
@app.route('/api/wait_for_element_visible', methods=['POST'])
def api_wait_for_element_visible():
    data = request.json
    selector = data.get('selector', '')
    timeout = data.get('timeout', 30000)
    
    if not selector:
        return jsonify({'error': '选择器不能为空'}), 400
    
    try:
        sync_wait_for_element_visible(selector, timeout)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取页面元素
@app.route('/api/page_elements', methods=['GET'])
def api_page_elements():
    try:
        elements = sync_get_page_elements()
        return jsonify({'success': True, 'elements': elements})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 检查是否存在测试用例
@app.route('/api/has_test_cases', methods=['GET'])
def api_has_test_cases():
    try:
        cases = db.get_all_test_cases()
        has_cases = len(cases) > 0
        return jsonify({'success': True, 'has_cases': has_cases})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取页面截图
@app.route('/api/screenshot', methods=['GET'])
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)