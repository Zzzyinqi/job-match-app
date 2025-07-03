import streamlit as st
import os
import re
import fitz  # PyMuPDF
from docx import Document
import pandas as pd
from datetime import datetime
import difflib

# 创建上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text_from_pdf(file_path):
    """从PDF文件中提取文本"""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    """从DOCX文件中提取文本"""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(file_path):
    """从TXT文件中提取文本"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def normalize_position(position):
    """标准化岗位名称"""
    if not position:
        return ""
    
    # 常见岗位名称映射
    position_mapping = {
        '前端': '前端开发', 'web前端': '前端开发', '前端工程师': '前端开发',
        '后端': '后端开发', 'java': 'Java开发', 'python': 'Python开发',
        'ui': 'UI设计', '美工': 'UI设计', '视觉设计': 'UI设计',
        '测试': '软件测试', 'qa': '软件测试', '测试工程师': '软件测试',
        '产品': '产品经理', '产品设计': '产品经理', 'pm': '产品经理',
        '运营': '运营专员', '新媒体': '新媒体运营', '内容运营': '内容运营',
        '销售': '销售代表', '业务员': '销售代表', 'bd': '商务拓展',
        '人事': '人力资源', 'hr': '人力资源', '招聘': '招聘专员',
        '财务': '财务会计', '会计': '财务会计', '出纳': '财务会计',
        '行政': '行政专员', '文员': '行政专员', '助理': '行政助理'
    }
    
    # 移除无关字符
    clean_position = re.sub(r'[、/（）()【】\[\]\s]', '', position).lower()
    
    # 应用映射
    for key, value in position_mapping.items():
        if key in clean_position:
            return value
    
    # 如果没有匹配的映射，返回原始值
    return position

def parse_document(text):
    """从求职者简历文本中提取结构化信息"""
    info = {
        '姓名': '',
        '年龄': '',
        '性别': '',
        '学历': '',
        '专业': '',
        '工作经验': '',
        '期望薪资': '',
        '求职岗位': '',
        # '技能': '',
        '联系方式': ''
    }
    
    # 姓名提取
    name_match = re.search(r'(姓名|名字|个人姓名|候选人姓名)[：:]\s*([\u4e00-\u9fa5A-Za-z·]+)', text)
    if name_match:
        info['姓名'] = name_match.group(2)
    
    # 年龄提取
    age_match = re.search(r'(年龄|岁数|出生年份)[：:]\s*(\d+)', text)
    if age_match:
        info['年龄'] = age_match.group(2)
    
    # 性别提取
    gender_match = re.search(r'(性别)[：:]\s*([男女])', text)
    if gender_match:
        info['性别'] = gender_match.group(2)
    
    # 学历提取
    education_match = re.search(r'(学历|教育背景|最高学历)[：:]\s*([\u4e00-\u9fa5]+)', text)
    if education_match:
        info['学历'] = education_match.group(2)
    
    # 专业提取
    major_match = re.search(r'(专业|所学专业|主修专业)[：:]\s*([\u4e00-\u9fa5A-Za-z]+)', text)
    if major_match:
        info['专业'] = major_match.group(2)
    
    # 工作经验提取
    exp_match = re.search(r'(工作经验|工作年限|从业时间)[：:]\s*(\d+)', text)
    if exp_match:
        info['工作经验'] = exp_match.group(2) + "年"
    
    # 期望薪资提取 - 支持中文描述
    salary_match = re.search(r'(期望薪资|薪资要求|期望月薪|期望年薪)[：:]\s*([\d\-~～kK万底薪提成薪金工资待遇薪\+＋加]+)', text)
    if salary_match:
        info['期望薪资'] = salary_match.group(2).strip()
    
    # 求职岗位提取 - 增强版
    position_patterns = [
        r'(求职意向|应聘职位|申请职位|期望职位|目标岗位|求职岗位)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()、/]+)',
        r'(期望工作|意向岗位|岗位意向)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()、/]+)',
        r'(申请|应聘|求职|职位)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()、/]+)',
        r'^[ \t]*(职位|岗位)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()、/]+)',
    ]
    
    position_found = False
    for pattern in position_patterns:
        match = re.search(pattern, text)
        if match:
            position = match.group(2).strip()
            position = re.sub(r'^[：:\s]+', '', position)
            info['求职岗位'] = position
            position_found = True
            break
    
    # 如果未匹配到，尝试跨行匹配
    if not position_found:
        match = re.search(
            r'(求职意向|应聘职位|申请职位|期望职位|目标岗位)[：:\s]*(.*?)(?=\n|$)', 
            text, 
            re.DOTALL
        )
        if match:
            position = match.group(2).strip()
            position = re.split(r'[\n\r]+', position)[0]
            info['求职岗位'] = position
    
    # 标准化岗位名称
    info['求职岗位'] = normalize_position(info['求职岗位'])
    
    # # 技能提取
    # skill_match = re.findall(r'(精通|熟悉|掌握|擅长)\s*([\u4e00-\u9fa5A-Za-z0-9#+]+)', text)
    # if skill_match:
    #     info['技能'] = "、".join([s[1] for s in skill_match])
    
    # 联系方式提取
    contact_match = re.search(r'(电话|手机|联系方式|联系电话)[：:]\s*([\d\-]+)', text)
    if contact_match:
        info['联系方式'] = contact_match.group(2)
    else:
        email_match = re.search(r'邮箱[：:]\s*([\w\.-]+@[\w\.-]+)', text)
        if email_match:
            info['联系方式'] = email_match.group(1)
    
    return info

def parse_job_document(text):
    """从企业文档文本中提取结构化信息"""
    info = {
        '企业名称': '',
        '招聘岗位': '',
        '学历要求': '',
        '薪资范围': '',
        '工作经验要求': '',
        '性别要求': '',
        # '职位描述': ''
    }
    
    # 企业名称提取
    company_match = re.search(r'(公司名称|企业名称|公司|招聘单位)[：:]\s*([\u4e00-\u9fa5A-Za-z0-9（）()]+)', text)
    if company_match:
        info['企业名称'] = company_match.group(2)
    
    # 招聘岗位
    position_match = re.search(r'(岗位名称|招聘岗位|职位名称|岗位|招聘职位)[：:]\s*([\u4e00-\u9fa5A-Za-z0-9、/]+)', text)
    if position_match:
        position = position_match.group(2).strip()
        info['招聘岗位'] = position
    
    # 标准化岗位名称
    info['招聘岗位'] = normalize_position(info['招聘岗位'])
    
    # 学历要求
    education_match = re.search(r'(学历要求|学历|教育背景要求)[：:]\s*([\u4e00-\u9fa5]+)', text)
    if education_match:
        info['学历要求'] = education_match.group(2)
    
    # 薪资范围提取 - 支持中文描述
    salary_match = re.search(r'(薪资范围|薪资|工资|薪酬范围)[：:]\s*([\d\-~～kK万底薪提成薪金工资待遇薪\+＋加]+)', text)
    if salary_match:
        info['薪资范围'] = salary_match.group(2).strip()
    
    # 工作经验要求
    exp_match = re.search(r'(工作经验要求|工作经验|工作年限|从业年限)[：:]\s*(\d+)', text)
    if exp_match:
        info['工作经验要求'] = exp_match.group(2) + "年"
    
    # 性别要求
    gender_match = re.search(r'(性别要求|性别)[：:]\s*([男女不限]+)', text)
    if gender_match:
        info['性别要求'] = gender_match.group(2)
    
    # # 职位描述（提取前100字）
    # desc_match = re.search(r'(职位描述|岗位职责|工作内容)[：:]\s*(.{1,1000})', text)
    # if desc_match:
    #     info['职位描述'] = desc_match.group(2)
    
    return info

def calculate_position_similarity(pos1, pos2):
    """计算两个岗位名称的相似度 (0-1)"""
    if not pos1 or not pos2:
        return 0.0
    
    # 完全匹配
    if pos1 == pos2:
        return 1.0
    
    # 包含关系检查
    if pos1 in pos2 or pos2 in pos1:
        return 0.7
    
    # 使用difflib计算序列匹配度
    seq_matcher = difflib.SequenceMatcher(None, pos1, pos2)
    similarity = seq_matcher.ratio()
    
    # 关键词匹配增强
    common_keywords = 0
    keywords = ['开发', '设计', '销售', '管理', '运营', '分析', '测试', '产品', '市场', '客服']
    
    for kw in keywords:
        if kw in pos1 and kw in pos2:
            common_keywords += 1
            # 每有一个共同关键词，增加相似度
            similarity += 0.1
    
    # 限制在0-1范围内
    return min(max(similarity, 0.0), 1.0)

    
    return 0  # 默认最低等级

def match_applicant_to_job(applicant_info, job_info):
    """匹配求职者与企业需求 - 关键指标不匹配时大幅降低整体匹配度"""
    match_result = {
        '学历匹配': '未评估',
        '薪资匹配': '未评估',
        '岗位匹配': '未评估',
        '性别匹配': '未评估',
        '工作经验匹配': '未评估',
        '整体匹配度': '未评估',
        '岗位相似度': '0%'
    }
    
    # 学历匹配
    education_levels = {
    '博士': 5, '博士研究生': 5, '博士及以上': 5,
    '硕士': 4, '硕士研究生': 4, '硕士及以上': 4,
    '本科': 3, '学士': 3, '大学': 3, '本科及以上': 3,
    '大专': 2, '专科': 2, '大专及以上': 2,
    '高中': 1, '中专': 1, '职高': 1, '高中及以上': 1,
    '初中': 0
}
    
    # 修改学历匹配逻辑
    def get_education_level(edu_str):
        """从学历字符串中提取核心等级"""
        # 首先检查整个字符串是否在字典中
        if edu_str in education_levels:
            return education_levels[edu_str]
        
        # 检查是否包含"及以上"、"以上"等要求
        if "及以上" in edu_str or "以上" in edu_str:
            # 提取核心学历词
            core_edu = re.sub(r'[及以]上', '', edu_str)
            if core_edu in education_levels:
                return education_levels[core_edu]
        
        # 最后尝试部分匹配
        for level in education_levels:
            if level in edu_str and level != "以上":  # 避免误匹配
                return education_levels[level]
        
        return 0  # 默认最低等级
    
    applicant_edu = applicant_info.get('学历', '')
    job_edu = job_info.get('学历要求', '')
    
    if applicant_edu and job_edu:
        applicant_level = get_education_level(applicant_edu)
        job_level = get_education_level(job_edu)
        
        # 检查企业要求是否包含"及以上"要求
        if "及以上" in job_edu or "以上" in job_edu:
            # 对于"及以上"要求，求职者等级必须达到或超过
            match_result['学历匹配'] = '符合' if applicant_level >= job_level else '不符合'
        else:
            # 对于明确要求，必须完全匹配
            match_result['学历匹配'] = '符合' if applicant_level == job_level else '不符合'
    
    # 薪资匹配
    applicant_salary = applicant_info.get('期望薪资', '')
    job_salary = job_info.get('薪资范围', '')
    
    if applicant_salary and job_salary:
        # 简化处理：提取薪资数字
        app_min, app_max = extract_salary_range(applicant_salary)
        job_min, job_max = extract_salary_range(job_salary)
        
        if app_min is not None and app_max is not None and job_min is not None and job_max is not None:
            # 检查求职者期望是否在企业范围内
            if app_min >= job_min and app_max <= job_max:
                match_result['薪资匹配'] = '符合'
            elif app_min <= job_max and app_max >= job_min:
                match_result['薪资匹配'] = '部分符合'
            else:
                match_result['薪资匹配'] = '不符合'
        else:
            match_result['薪资匹配'] = '无法评估'
    
    # 岗位匹配
    applicant_position = applicant_info.get('求职岗位', '')
    job_position = job_info.get('招聘岗位', '')
    
    # 计算岗位相似度
    position_similarity = calculate_position_similarity(applicant_position, job_position)
    match_result['岗位相似度'] = f"{position_similarity * 100:.0f}%"
    
    if applicant_position and job_position:
        # 基于相似度判断匹配程度
        if position_similarity >= 0.85:
            match_result['岗位匹配'] = '高度符合'
        elif position_similarity >= 0.6:
            match_result['岗位匹配'] = '部分符合'
        else:
            match_result['岗位匹配'] = '不符合'
    else:
        match_result['岗位匹配'] = '未评估'
    
    # 性别匹配
    applicant_gender = applicant_info.get('性别', '')
    job_gender = job_info.get('性别要求', '')
    
    if applicant_gender and job_gender:
        if job_gender == '不限' or job_gender == '无要求' or '不限' in job_gender:
            match_result['性别匹配'] = '符合'
        else:
            match_result['性别匹配'] = '符合' if applicant_gender == job_gender else '不符合'
    
    # 工作经验匹配
    applicant_exp = applicant_info.get('工作经验', '')
    job_exp = job_info.get('工作经验要求', '')
    
    if applicant_exp and job_exp:
        try:
            app_exp_years = int(re.search(r'\d+', applicant_exp).group())
            job_exp_years = int(re.search(r'\d+', job_exp).group())
            match_result['工作经验匹配'] = '符合' if app_exp_years >= job_exp_years else '不符合'
        except:
            match_result['工作经验匹配'] = '无法评估'
    
    # 计算整体匹配度 - 关键指标不匹配时大幅降低匹配度
    # 定义关键指标和普通指标
    critical_fields = ['岗位匹配', '学历匹配']  # 关键指标
    normal_fields = ['薪资匹配', '性别匹配', '工作经验匹配']  # 普通指标
    
    # 定义各匹配结果的权重
    weight_map = {
        '高度符合': 1.0,
        '符合': 1.0,
        '部分符合': 0.6,
        '不符合': 0.0,
        '无法评估': 0.5,  # 无法评估按50%计分
        '未评估': 0.0
    }
    
    # 关键指标权重因子 (当关键指标不符合时，整体匹配度大幅降低)
    critical_penalty = 0.3  # 关键指标不符合时的惩罚因子
    
    # 计算匹配度
    total_score = 0.0
    max_score = 0.0
    critical_fail = False
    
    # 处理关键指标
    for field in critical_fields:
        result = match_result[field]
        if result != '未评估':
            score = weight_map.get(result, 0.0)
            
            # 如果关键指标不符合，设置标志并应用惩罚
            if result == '不符合':
                critical_fail = True
                score *= critical_penalty
            
            total_score += score * 2.0  # 关键指标权重加倍
            max_score += 2.0
    
    # 处理普通指标
    for field in normal_fields:
        result = match_result[field]
        if result != '未评估':
            score = weight_map.get(result, 0.0)
            
            # 如果有关键指标不符合，普通指标得分也降低
            if critical_fail:
                score *= critical_penalty
            
            total_score += score
            max_score += 1.0
    
    # 计算整体匹配度百分比
    if max_score > 0:
        match_percentage = int((total_score / max_score) * 100)
        
        # 如果关键指标不符合，匹配度上限设为50%
        if critical_fail and match_percentage > 50:
            match_percentage = 50
            
        match_result['整体匹配度'] = f"{match_percentage}%"
    else:
        match_result['整体匹配度'] = '无法计算'
    
    return match_result

def extract_salary_range(salary_str):
    """从薪资字符串中提取数字范围，支持中文描述"""
    # 处理常见薪资格式：10k-20k, 10,000-20,000, 1万-2万, 底薪10k+提成
    salary_str = salary_str.replace(',', '').replace('，', '')
    
    # 统一单位转换 - 提取所有数字部分
    numbers = []
    if '万' in salary_str or 'k' in salary_str.lower():
        # 查找所有数字和单位
        num_units = re.findall(r'(\d+\.?\d*)([万kK]?)', salary_str)
        for num, unit in num_units:
            num = float(num)
            if unit == '万':
                num *= 10000
            elif unit.lower() == 'k':
                num *= 1000
            numbers.append(num)
    else:
        # 提取纯数字
        numbers = [float(num) for num in re.findall(r'\d+\.?\d*', salary_str)]
    
    # 处理提取到的数字
    if numbers:
        if len(numbers) >= 2:
            return min(numbers), max(numbers)
        else:
            return numbers[0], numbers[0]
    
    return None, None

def save_uploaded_file(uploaded_file, file_type):
    """保存上传的文件"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_ext = uploaded_file.name.split('.')[-1]
    filename = f"{file_type}_{timestamp}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def main():
    st.title("就业面试智能体系统")
    st.subheader("求职者与企业信息匹配平台")
    
    # 初始化session state
    if 'applicant_info' not in st.session_state:
        st.session_state.applicant_info = {}
    if 'job_info' not in st.session_state:
        st.session_state.job_info = {}
    if 'match_result' not in st.session_state:
        st.session_state.match_result = {}
    
    # 上传功能
    st.sidebar.header("文件上传")
    upload_option = st.sidebar.radio("选择上传类型", ["企业信息", "求职者简历"])
    
    if upload_option == "企业信息":
        uploaded_file = st.sidebar.file_uploader(
            "上传企业信息文档 (doc, docx, pdf, txt)",
            type=["doc", "docx", "pdf", "txt"]
        )
        
        if uploaded_file:
            file_path = save_uploaded_file(uploaded_file, "job")
            file_ext = file_path.split('.')[-1].lower()
            
            try:
                if file_ext == "pdf":
                    text = extract_text_from_pdf(file_path)
                elif file_ext in ["doc", "docx"]:
                    text = extract_text_from_docx(file_path)
                else:  # txt
                    text = extract_text_from_txt(file_path)
                
                # 使用企业文档解析函数
                st.session_state.job_info = parse_job_document(text)
                
                # 如果解析失败，使用文件名作为企业名称
                if not st.session_state.job_info.get('企业名称'):
                    st.session_state.job_info['企业名称'] = uploaded_file.name.split('.')[0]
                
                st.sidebar.success("企业信息解析成功！")
                
            except Exception as e:
                st.sidebar.error(f"文件解析错误: {str(e)}")
    
    else:  # 求职者简历
        uploaded_file = st.sidebar.file_uploader(
            "上传求职者简历 (doc, docx, pdf, txt)",
            type=["doc", "docx", "pdf", "txt"]
        )
        
        if uploaded_file:
            file_path = save_uploaded_file(uploaded_file, "applicant")
            file_ext = file_path.split('.')[-1].lower()
            
            try:
                if file_ext == "pdf":
                    text = extract_text_from_pdf(file_path)
                elif file_ext in ["doc", "docx"]:
                    text = extract_text_from_docx(file_path)
                else:  # txt
                    text = extract_text_from_txt(file_path)
                
                st.session_state.applicant_info = parse_document(text)
                st.sidebar.success("求职者简历解析成功！")
                
            except Exception as e:
                st.sidebar.error(f"文件解析错误: {str(e)}")
    
    # 显示解析结果
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("企业信息")
        if st.session_state.job_info:
            job_df = pd.DataFrame.from_dict(
                st.session_state.job_info, 
                orient='index', 
                columns=['值']
            )
            st.dataframe(job_df)
        else:
            st.info("请上传企业信息文档")
    
    with col2:
        st.subheader("求职者信息")
        if st.session_state.applicant_info:
            applicant_df = pd.DataFrame.from_dict(
                st.session_state.applicant_info, 
                orient='index', 
                columns=['值']
            )
            st.dataframe(applicant_df)
        else:
            st.info("请上传求职者简历")
    
    # 匹配按钮
    if st.button("进行匹配分析", use_container_width=True):
        if st.session_state.job_info and st.session_state.applicant_info:
            st.session_state.match_result = match_applicant_to_job(
                st.session_state.applicant_info,
                st.session_state.job_info
            )
            st.success("匹配分析完成！")
        else:
            st.warning("请先上传企业信息和求职者简历")
    
    # 显示匹配结果
    if st.session_state.match_result:
        st.subheader("匹配分析结果")
        
        # 创建结果数据框，排除岗位相似度（将在后面单独显示）
        display_result = {k: v for k, v in st.session_state.match_result.items() if k != '岗位相似度'}
        match_df = pd.DataFrame.from_dict(
            display_result, 
            orient='index', 
            columns=['结果']
        )
        st.dataframe(match_df)
        
        # 显示岗位相似度详情
        applicant_position = st.session_state.applicant_info.get('求职岗位', '无')
        job_position = st.session_state.job_info.get('招聘岗位', '无')
        similarity = st.session_state.match_result.get('岗位相似度', '0%')
        
        st.write(f"**岗位匹配详情**:")
        st.write(f"- 求职者岗位: `{applicant_position}`")
        st.write(f"- 企业岗位: `{job_position}`")
        st.write(f"- 岗位相似度: `{similarity}`")
        
        # 可视化匹配度
        overall_match = st.session_state.match_result.get('整体匹配度', '0%')
        
        # 只有当匹配度是百分比时才显示进度条
        if '%' in overall_match:
            try:
                match_percentage = int(overall_match.strip('%'))
                st.metric("整体匹配度", overall_match)
                st.progress(match_percentage / 100)
                
                # 关键指标检查
                critical_fail = False
                critical_fields = ['岗位匹配', '学历匹配']
                for field in critical_fields:
                    result = st.session_state.match_result.get(field, '')
                    if '不符合' in result:
                        critical_fail = True
                        st.warning(f"⚠️ 关键指标 '{field}' 不符合要求，匹配度大幅降低")
                
                # 匹配建议
                if match_percentage >= 80:
                    st.success("👍 高度匹配：求职者非常适合该职位")
                elif match_percentage >= 60:
                    st.info("👌 中度匹配：求职者基本符合要求")
                elif match_percentage >= 40:
                    st.warning("⚠️ 低度匹配：存在明显不匹配项")
                else:
                    st.error("❌ 不匹配：求职者与职位要求差距较大")
                    
                # 关键指标不符合时的特殊提示
                if critical_fail and match_percentage > 0:
                    st.error("⛔ 关键指标（岗位/学历）不符合，求职者不符合企业基本要求")
                
            except ValueError:
                st.warning("无法计算匹配度百分比")
        else:
            st.warning(f"匹配度数据异常: {overall_match}")

if __name__ == "__main__":
    main()
    
#streamlit run d:/model/match_job.py