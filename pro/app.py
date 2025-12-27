from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import FLASK_CONFIG
from dao import ResearchDAO
from datetime import datetime

#  初始化Flask应用
app = Flask(__name__,static_folder='static', static_url_path='/static')
app.config.from_mapping(FLASK_CONFIG)
dao = ResearchDAO()

# 基础布局路由
@app.route('/')
def index():
    return redirect(url_for('project_list'))

# ========== 科研项目路由 ==========
# 项目列表页
@app.route('/projects')
def project_list():
    projects = dao.get_all_projects()
    return render_template('projects.html', projects=projects)

# 新增项目
@app.route('/project/add', methods=['POST'])
def add_project():
    if request.method == 'POST':
        try:
            project_data = {
                'project_id': request.form['project_id'],
                'project_name': request.form['project_name'],
                'leader_id': request.form['leader_id'],
                'apply_unit': request.form['apply_unit'],
                'approval_time': datetime.strptime(request.form['approval_time'], '%Y-%m-%d').date(),
                'project_status': request.form['project_status'],
                'research_field': request.form['research_field'],
                'conclusion_time': datetime.strptime(request.form['conclusion_time'], '%Y-%m-%d').date() if request.form['conclusion_time'] else None
            }
            success, msg = dao.add_project(project_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('project_list'))

# 项目详情页
@app.route('/project/<project_id>')
def project_detail(project_id):
    project = dao.get_project_by_id(project_id)
    if not project:
        flash("项目不存在", 'danger')
        return redirect(url_for('project_list'))
    collections = dao.get_collections_by_project(project_id)
    achievements = dao.get_achievements_by_project(project_id)
    return render_template('detail.html', project=project, collections=collections, achievements=achievements)

# 更新项目状态
@app.route('/project/update_status/<project_id>', methods=['POST'])
def update_project_status(project_id):
    new_status = request.form.get('new_status')
    if not new_status:
        flash("状态不能为空", 'danger')
        return redirect(url_for('project_detail', project_id=project_id))
    success, msg = dao.update_project_status(project_id, new_status)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('project_detail', project_id=project_id))

# 删除项目
@app.route('/project/delete/<project_id>')
def delete_project(project_id):
    success, msg = dao.delete_project(project_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('project_list'))

# ========== 采集记录路由 ==========
# 新增采集记录
@app.route('/collection/add', methods=['POST'])
def add_collection():
    if request.method == 'POST':
        try:
            collection_data = {
                'collection_id': request.form['collection_id'],
                'project_id': request.form['project_id'],
                'collector_id': request.form['collector_id'],
                'collection_time': datetime.strptime(request.form['collection_time'], '%Y-%m-%dT%H:%M'),
                'collection_content': request.form['collection_content'],
                'data_source': request.form['data_source']
            }
            success, msg = dao.add_collection(collection_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('project_detail', project_id=request.form['project_id']))

# 删除采集记录
@app.route('/collection/delete/<collection_id>/<project_id>')
def delete_collection(collection_id, project_id):
    success, msg = dao.delete_collection(collection_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('project_detail', project_id=project_id))

# ========== 科研成果路由 ==========
# 新增科研成果
@app.route('/achievement/add', methods=['POST'])
def add_achievement():
    if request.method == 'POST':
        try:
            achievement_data = {
                'achievement_id': request.form['achievement_id'],
                'project_id': request.form['project_id'],
                'achievement_type': request.form['achievement_type'],
                'achievement_name': request.form['achievement_name'],
                'publish_time': datetime.strptime(request.form['publish_time'], '%Y-%m-%d').date(),
                'share_permission': request.form['share_permission'],
                'file_path': request.form['file_path']
            }
            success, msg = dao.add_achievement(achievement_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('project_detail', project_id=request.form['project_id']))

# 删除科研成果
@app.route('/achievement/delete/<achievement_id>/<project_id>')
def delete_achievement(achievement_id, project_id):
    success, msg = dao.delete_achievement(achievement_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/collections')
def collection_list():
    """采集记录列表页"""
    collections = dao.get_all_collections()
    return render_template('collection_list.html', collections=collections)


@app.route('/collection/<collection_id>')
def collection_detail(collection_id):
    """采集记录详情页"""
    collection = dao.get_collection_by_id(collection_id)
    if not collection:
        flash("采集记录不存在", 'danger')
        return redirect(url_for('collection_list'))

    # 获取关联的监测数据
    monitor_data = dao.get_monitor_data_by_collection(collection_id)
    return render_template('collection_detail.html', collection=collection, monitor_data=monitor_data)


@app.route('/collection/add/standalone', methods=['POST'])
def add_collection_standalone():
    """独立新增采集记录（非项目内）"""
    if request.method == 'POST':
        try:
            collection_data = {
                'collection_id': request.form['collection_id'],
                'project_id': request.form.get('project_id'),  # 可选
                'collector_id': request.form['collector_id'],
                'collection_time': request.form['collection_time'],
                'collection_content': request.form['collection_content'],
                'data_source': request.form['data_source']
            }
            success, msg = dao.add_collection(collection_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('collection_list'))


@app.route('/collection/update/<collection_id>', methods=['POST'])
def update_collection(collection_id):
    """更新采集记录"""
    if request.method == 'POST':
        try:
            update_data = {}
            if 'collector_id' in request.form:
                update_data['collector_id'] = request.form['collector_id']
            if 'collection_content' in request.form:
                update_data['collection_content'] = request.form['collection_content']
            if 'data_source' in request.form:
                update_data['data_source'] = request.form['data_source']

            success, msg = dao.update_collection(collection_id, update_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('collection_detail', collection_id=collection_id))


@app.route('/collection/delete/<collection_id>')
def delete_collection_standalone(collection_id):
    """独立删除采集记录"""
    success, msg = dao.delete_collection(collection_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('collection_list'))

# ========== 新增：科研成果独立路由 ==========
@app.route('/achievements')
def achievement_list():
    """科研成果列表页"""
    achievements = dao.get_all_achievements()
    return render_template('achievement_list.html', achievements=achievements)


@app.route('/achievement/<achievement_id>')
def achievement_detail(achievement_id):
    """科研成果详情页"""
    achievement = dao.get_achievement_by_id(achievement_id)
    if not achievement:
        flash("科研成果不存在", 'danger')
        return redirect(url_for('achievement_list'))

    # 获取共享记录
    shared_projects = dao.get_shared_achievements(achievement_id)
    return render_template('achievement_detail.html', achievement=achievement, shared_projects=shared_projects)


@app.route('/achievement/add/standalone', methods=['POST'])
def add_achievement_standalone():
    """独立新增科研成果（非项目内）"""
    if request.method == 'POST':
        try:
            achievement_data = {
                'achievement_id': request.form['achievement_id'],
                'project_id': request.form.get('project_id'),  # 可选
                'achievement_type': request.form['achievement_type'],
                'achievement_name': request.form['achievement_name'],
                'publish_time': request.form['publish_time'],
                'share_permission': request.form['share_permission'],
                'file_path': request.form.get('file_path', '')
            }
            success, msg = dao.add_achievement(achievement_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('achievement_list'))


@app.route('/achievement/update/<achievement_id>', methods=['POST'])
def update_achievement(achievement_id):
    """更新科研成果"""
    if request.method == 'POST':
        try:
            update_data = {}
            if 'achievement_name' in request.form:
                update_data['achievement_name'] = request.form['achievement_name']
            if 'share_permission' in request.form:
                update_data['share_permission'] = request.form['share_permission']
            if 'file_path' in request.form:
                update_data['file_path'] = request.form['file_path']

            success, msg = dao.update_achievement(achievement_id, update_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(url_for('achievement_detail', achievement_id=achievement_id))


@app.route('/achievement/delete/<achievement_id>')
def delete_achievement_standalone(achievement_id):
    """独立删除科研成果"""
    success, msg = dao.delete_achievement(achievement_id)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('achievement_list'))


# ========== 新增：关联表操作路由 ==========
@app.route('/achievement/share', methods=['POST'])
def share_achievement():
    """共享科研成果到项目"""
    if request.method == 'POST':
        try:
            share_data = {
                'project_id': request.form['project_id'],
                'achievement_id': request.form['achievement_id'],
                'share_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'authorizer_id': request.form['authorizer_id']
            }
            success, msg = dao.add_achievement_share(share_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(request.referrer or url_for('achievement_list'))


@app.route('/collection/link_monitor', methods=['POST'])
def link_monitor_data():
    """关联监测数据到采集记录"""
    if request.method == 'POST':
        try:
            rel_data = {
                'collection_id': request.form['collection_id'],
                'monitor_data_id': request.form['monitor_data_id'],
                'data_type': request.form['data_type']
            }
            success, msg = dao.add_monitor_data_rel(rel_data)
            flash(msg, 'success' if success else 'danger')
        except Exception as e:
            flash(f"参数错误：{str(e)}", 'danger')
    return redirect(request.referrer or url_for('collection_list'))

# ========== 新增：API接口（可选） ==========
@app.route('/api/collections')
def api_collections():
    """采集记录API"""
    collections = dao.get_all_collections()
    return jsonify([{
        'collection_id': c.collection_id,
        'project_id': c.project_id,
        'collector_id': c.collector_id,
        'collection_time': c.collection_time.strftime('%Y-%m-%d %H:%M:%S'),
        'data_source': c.data_source
    } for c in collections])


@app.route('/api/achievements')
def api_achievements():
    """科研成果API"""
    achievements = dao.get_all_achievements()
    return jsonify([{
        'achievement_id': a.achievement_id,
        'project_id': a.project_id,
        'achievement_type': a.achievement_type,
        'achievement_name': a.achievement_name,
        'publish_time': a.publish_time.strftime('%Y-%m-%d'),
        'share_permission': a.share_permission
    } for a in achievements])


if __name__ == '__main__':
    # 先执行 init_db.py 创建数据库和表，再运行此文件
    app.run(host='0.0.0.0', port=5000)