from database import Database

# 初始化数据库
db = Database()

# 创建一个新的测试用例，导航到百度首页
case_id = db.create_test_case_v2(
    project_id=1,
    name="导航到百度首页",
    url="https://www.baidu.com",
    description="测试导航到百度首页的功能",
    precondition="",
    expected_result="成功打开百度首页"
)

print(f"创建的测试用例ID: {case_id}")

# 为测试用例创建一个导航步骤
step_id = db.create_test_step(
    case_id=case_id,
    action="navigate",
    selector_type="",
    selector_value="",
    input_value="",
    description="导航到百度首页",
    step_order=1,
    page_name="百度首页",
    swipe_x="",
    swipe_y="",
    url="https://www.baidu.com"
)

print(f"创建的测试步骤ID: {step_id}")
print("测试用例创建完成，请运行此测试用例验证浏览器是否正常显示")