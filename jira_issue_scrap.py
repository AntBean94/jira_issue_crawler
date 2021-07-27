import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import IGNORED_EXCEPTIONS


# 팀 정보 로드
r = open('sprint_numbers.txt', 'r')
sprint_numbers = []
while True:
    number = r.readline().rstrip()
    if not number:
        break
    sprint_numbers.append(number)
num_of_teams = len(sprint_numbers)
print()
print('-- 스프린트 넘버 확인 --')
for i in range(num_of_teams):
    print(f'{i+1}팀: ', sprint_numbers[i])

# member 정보 로드
r = open('members.txt', 'r', encoding='utf-8')
# {'이름': [진행 중, 할 일, 완료, 담당(합), 생성, 서브태스크, 스토리포인트]}
jira_report = {}
while True:
    member = r.readline().rstrip()
    if not member:
        break
    jira_report[member] = [0] * 7
issue_idx = {'진행 중': 0, '할 일': 1, '완료': 2}
# 미할당 이슈 체크 리스트
jira_report['할당되지 않음'] = [0] * num_of_teams

# 코치 로그인 정보 로드
secrets = json.loads(open('secrets.json').read())
coach_ID = secrets['COACH_ID']
coach_PASSWORD = secrets['COACH_PASSWORD']

# 데이터 기록
f = open('jira_issue_result.csv', 'w')

# 웹 드라이버 설정 
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')   # 화면 로드 설정(주석처리하면 안뜸)
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# 웹 드라이버 객체 생성
driver = webdriver.Chrome('chromedriver', options=chrome_options)

url = f'https://jira.ssafy.com/projects/{sprint_numbers[0]}/issues?filter=allissues'
driver.get(url)
sleep(2)
driver.find_element_by_css_selector('#userId').send_keys(coach_ID)
driver.find_element_by_css_selector('#userPwd').send_keys(coach_PASSWORD)
driver.find_element_by_css_selector('#userPwd').send_keys(Keys.ENTER)
sleep(3)

ignored_exceptions = (NoSuchElementException, StaleElementReferenceException, TimeoutException, )
# 지라 이슈 스크래핑 스따뚜
for team in range(num_of_teams):
    print(f'{team+1}팀 탐색 중...')
    url = f'https://jira.ssafy.com/projects/{sprint_numbers[team]}/issues?filter=allissues'
    driver.get(url)
    sleep(3)

    # 이슈 데이터 스크랩
    issue_page = int(driver.find_element_by_css_selector('.pagination').get_attribute('data-displayable-total'))
    page = (issue_page // 50) + 1 if issue_page % 50 else issue_page // 50
    for p in range(page):
        issue_path = f'//*[@id="content"]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div/div[1]/div[2]/div/ol/li'
        issues = driver.find_elements_by_xpath(issue_path)
        sleep(2)
        for issue in issues:
            issue.click()
            sleep(0.5)
            
            # 보고자
            reporter_path = '//*[@id="reporter-val"]/span'
            reporter = WebDriverWait(driver, 5, ignored_exceptions==ignored_exceptions).until(expected_conditions.presence_of_element_located((By.XPATH, reporter_path))).text
            if reporter:
                jira_report[reporter][4] += 1

            # 담당자
            assignee_path = '//*[@id="assignee-val"]/span'
            assignee = WebDriverWait(driver, 1000, ignored_exceptions=ignored_exceptions).until(expected_conditions.presence_of_element_located((By.XPATH, assignee_path))).text
            if assignee:
                jira_report[assignee][3] += 1
            else:   
                # 담당자가 정해져 있지 않으면 미할당 리스트에 추가
                jira_report['할당되지 않음'][team] += 1
                continue

            # 진행 중, 할 일, 완료 체크
            status_path = '//*[@id="status-val"]/span'
            status = WebDriverWait(driver, 1000, ignored_exceptions=ignored_exceptions).until(expected_conditions.presence_of_element_located((By.XPATH, status_path))).text
            jira_report[assignee][issue_idx[status]] += 1

            # 서브태스크 여부 체크 
            issue_path = '//*[@id="type-val"]'
            issue_type = WebDriverWait(driver, 1000, ignored_exceptions=ignored_exceptions).until(expected_conditions.presence_of_element_located((By.XPATH, issue_path))).text
            if issue_type=='부작업':
                jira_report[assignee][5] += 1

            # 스토리포인트 체크
            # story_point = driver.find_element_by_xpath('//*[@id="customfield_10106-val"]').text
            # if story_point.isdigit():
            #     jira_report[assignee][6] += int(story_point)

        # 페이지 체크 => 로직 수정 필요
        print(jira_report)
        if p!=page-1:
            driver.find_element_by_css_selector('.nav-next').click()
            sleep(0.5)

print(jira_report)

f.write('이름, 진행 중, 할 일, 완료, 담당(합), 생성, 서브태스크, 스토리포인트\n')
for member, value in jira_report.items():
    line = member + ", " + ", ".join(map(str, value)) + '\n'
    f.write(line)
