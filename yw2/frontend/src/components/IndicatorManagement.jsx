// src/components/IndicatorManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://192.168.69.97:5001/api';

const IndicatorManagement = ({ onIndicatorUpdate }) => {
  const [indicators, setIndicators] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingIndicator, setEditingIndicator] = useState(null);
  const [formData, setFormData] = useState({
    indicator_id: '',
    indicator_name: '',
    unit: '',
    standard_upper: '',
    standard_lower: '',
    monitor_freq: '日'
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadIndicators();
  }, []);

  const loadIndicators = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/indicators`);
      if (res.data.success) {
        setIndicators(res.data.indicators || []);
      }
    } catch (error) {
      console.error('加载监测指标失败:', error);
      setError('加载失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAddIndicator = () => {
    setEditingIndicator(null);
    setFormData({
      indicator_id: '',
      indicator_name: '',
      unit: '',
      standard_upper: '',
      standard_lower: '',
      monitor_freq: '日'
    });
    setShowModal(true);
    setError('');
  };

  const handleEditIndicator = (indicator) => {
    setEditingIndicator(indicator);
    setFormData({
      indicator_id: indicator.indicator_id,
      indicator_name: indicator.indicator_name,
      unit: indicator.unit || '',
      standard_upper: indicator.standard_upper,
      standard_lower: indicator.standard_lower,
      monitor_freq: indicator.monitor_freq || '日'
    });
    setShowModal(true);
    setError('');
  };

 // 修改：更新指标后的处理
const handleSubmit = async (e) => {
  e.preventDefault();
  setError('');

  try {
    if (editingIndicator) {
      // 更新指标
      const res = await axios.put(
        `${API_BASE_URL}/indicators/${editingIndicator.indicator_id}/update`,
        formData
      );

      if (res.data.success) {
        setShowModal(false);
        loadIndicators();

        // 提示用户重新计算异常数据
        const shouldRecalc = window.confirm('指标更新成功！是否立即重新计算该指标的异常数据？');

        if (shouldRecalc) {
          try {
            const recalcRes = await axios.post(
              `${API_BASE_URL}/environment/data/recalculate-abnormal-by-indicator`,
              { indicator_id: editingIndicator.indicator_id }
            );

            if (recalcRes.data.success) {
              const affected = recalcRes.data.affected || 0;
              alert(`异常数据重新计算完成，影响数据: ${affected} 条`);
            } else {
              alert('重新计算异常数据时出错。');
            }
          } catch (recalcError) {
            console.error('重新计算异常数据失败:', recalcError);
            alert('异常数据将在下次数据更新时自动重新计算。');
          }
        }

        // 调用回调函数刷新前端显示
        if (onIndicatorUpdate) {
          onIndicatorUpdate(true);
        }
      } else {
        setError(res.data.error || '更新失败');
      }
    } else {
      // 新增指标
      const res = await axios.post(`${API_BASE_URL}/indicators/add`, formData);
      if (res.data.success) {
        alert('新增成功！');
        setShowModal(false);
        loadIndicators();
        if (onIndicatorUpdate) {
          onIndicatorUpdate(false);
        }
      } else {
        setError(res.data.error || '新增失败');
      }
    }
  } catch (error) {
    console.error('提交失败:', error);
    setError('提交失败: ' + (error.response?.data?.error || error.message));
  }
};

  const handleDeleteIndicator = async (indicatorId) => {
    if (!window.confirm('确定要删除该监测指标吗？删除后相关数据将不再进行异常检测。')) {
      return;
    }

    try {
      const res = await axios.delete(`${API_BASE_URL}/indicators/${indicatorId}/delete`);
      if (res.data.success) {
        alert('删除成功！');
        loadIndicators();

        // 调用回调函数刷新异常数据
        if (onIndicatorUpdate) {
          onIndicatorUpdate(true);
        }
      } else {
        alert('删除失败: ' + (res.data.error || '未知错误'));
      }
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setError('');
  };

  return (
    <div className="data-management">
      <div className="section-header">
        <h2>监测指标管理</h2>
        <div className="controls">
          <button onClick={loadIndicators} className="btn-refresh">
            刷新列表
          </button>
          <button onClick={handleAddIndicator} className="btn-action">
            新增指标
          </button>
          <button onClick={() => {
            if (onIndicatorUpdate) {
              onIndicatorUpdate(true);
              alert('已触发异常数据重新计算');
            }
          }} className="btn-action" style={{backgroundColor: '#ffc107', color: '#333'}}>
            重新计算异常
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" style={{
          backgroundColor: '#f8d7da',
          color: '#721c24',
          padding: '10px',
          borderRadius: '4px',
          marginBottom: '15px'
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>指标编号</th>
                <th>指标名称</th>
                <th>计量单位</th>
                <th>阈值下限</th>
                <th>阈值上限</th>
                <th>监测频率</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {indicators.length > 0 ? indicators.map((indicator) => (
                <tr key={indicator.indicator_id}>
                  <td>{indicator.indicator_id}</td>
                  <td>{indicator.indicator_name}</td>
                  <td>{indicator.unit || '-'}</td>
                  <td>{indicator.standard_lower}</td>
                  <td>{indicator.standard_upper}</td>
                  <td>{indicator.monitor_freq}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleEditIndicator(indicator)}
                        className="btn-action"
                        style={{
                          backgroundColor: '#17a2b8',
                          padding: '4px 10px',
                          fontSize: '0.85rem'
                        }}
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteIndicator(indicator.indicator_id)}
                        className="btn-action"
                        style={{
                          backgroundColor: '#dc3545',
                          padding: '4px 10px',
                          fontSize: '0.85rem'
                        }}
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>
                    暂无监测指标数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 模态框 */}
      {showModal && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="modal" style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            width: '500px',
            maxWidth: '90%',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <h3 style={{ marginBottom: '20px' }}>
              {editingIndicator ? '编辑监测指标' : '新增监测指标'}
            </h3>

            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  指标编号 *
                </label>
                <input
                  type="text"
                  name="indicator_id"
                  value={formData.indicator_id}
                  onChange={handleInputChange}
                  disabled={editingIndicator}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  指标名称 *
                </label>
                <input
                  type="text"
                  name="indicator_name"
                  value={formData.indicator_name}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  计量单位
                </label>
                <input
                  type="text"
                  name="unit"
                  value={formData.unit}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                    阈值下限 *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    name="standard_lower"
                    value={formData.standard_lower}
                    onChange={handleInputChange}
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                    required
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                    阈值上限 *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    name="standard_upper"
                    value={formData.standard_upper}
                    onChange={handleInputChange}
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                    required
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  监测频率
                </label>
                <select
                  name="monitor_freq"
                  value={formData.monitor_freq}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="小时">小时</option>
                  <option value="日">日</option>
                  <option value="周">周</option>
                  <option value="月">月</option>
                </select>
              </div>

              {error && (
                <div className="error-message" style={{
                  backgroundColor: '#f8d7da',
                  color: '#721c24',
                  padding: '10px',
                  borderRadius: '4px',
                  marginBottom: '15px'
                }}>
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={handleCloseModal}
                  style={{
                    padding: '8px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  取消
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 20px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  {editingIndicator ? '更新' : '新增'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndicatorManagement;
