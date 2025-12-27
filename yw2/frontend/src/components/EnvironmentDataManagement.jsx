// src/components/EnvironmentDataManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://192.168.69.97:5001/api';

const EnvironmentDataManagement = ({ onDataUpdate }) => {
  const [dataList, setDataList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [editingData, setEditingData] = useState(null);
  const [indicators, setIndicators] = useState([]);
  const [devices, setDevices] = useState([]);
  const [regions, setRegions] = useState([]);
  const [filters, setFilters] = useState({
    region_id: '',
    indicator_id: '',
    start_date: '',
    end_date: ''
  });
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    pages: 0
  });
  const [formData, setFormData] = useState({
    indicator_id: '',
    device_id: '',
    region_id: '',
    monitor_value: '',
    data_quality: '中',
    collection_time: new Date().toISOString().slice(0, 16).replace('T', ' ')
  });
  const [batchData, setBatchData] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
    loadDropdownData();
  }, [pagination.page, filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        ...filters
      };

      const res = await axios.get(`${API_BASE_URL}/environment/data/all`, { params });
      if (res.data.success) {
        setDataList(res.data.data || []);
        setPagination(res.data.pagination || pagination);
      }
    } catch (error) {
      console.error('加载环境监测数据失败:', error);
      setError('加载失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadDropdownData = async () => {
    try {
      // 加载指标
      const indicatorsRes = await axios.get(`${API_BASE_URL}/indicators`);
      if (indicatorsRes.data.success) {
        setIndicators(indicatorsRes.data.indicators || []);
      }

      // 加载设备
      const devicesRes = await axios.get(`${API_BASE_URL}/devices/all`);
      if (devicesRes.data.success) {
        setDevices(devicesRes.data.devices || []);
      }

      // 加载区域
      const regionsRes = await axios.get(`${API_BASE_URL}/regions`);
      if (regionsRes.data.success) {
        setRegions(regionsRes.data.regions || []);
      }
    } catch (error) {
      console.error('加载下拉数据失败:', error);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
    // 重置页码到第一页
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAddData = () => {
    setEditingData(null);
    setFormData({
      indicator_id: '',
      device_id: '',
      region_id: '',
      monitor_value: '',
      data_quality: '中',
      collection_time: new Date().toISOString().slice(0, 16).replace('T', ' ')
    });
    setShowModal(true);
    setError('');
  };

  const handleEditData = (data) => {
    setEditingData(data);
    setFormData({
      indicator_id: data.indicator_id,
      device_id: data.device_id,
      region_id: data.region_id,
      monitor_value: data.monitor_value,
      data_quality: data.data_quality,
      collection_time: data.collection_time ?
        new Date(data.collection_time).toISOString().slice(0, 16).replace('T', ' ') :
        new Date().toISOString().slice(0, 16).replace('T', ' ')
    });
    setShowModal(true);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const formattedData = {
        ...formData,
        collection_time: formData.collection_time.replace(' ', ' ') + ':00'
      };

      if (editingData) {
        // 更新数据
        const res = await axios.put(
          `${API_BASE_URL}/environment/data/${editingData.data_id}/update`,
          formattedData
        );
        if (res.data.success) {
          alert('更新成功！');
          setShowModal(false);
          loadData();
          if (onDataUpdate) {
            onDataUpdate(false);
          }
        } else {
          setError(res.data.error || '更新失败');
        }
      } else {
        // 新增数据
        const res = await axios.post(`${API_BASE_URL}/environment/data/add`, formattedData);
        if (res.data.success) {
          alert('新增成功！');
          setShowModal(false);
          loadData();
          if (onDataUpdate) {
            onDataUpdate(false);
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

  const handleDeleteData = async (dataId) => {
    if (!window.confirm('确定要删除该监测数据吗？')) {
      return;
    }

    try {
      const res = await axios.delete(`${API_BASE_URL}/environment/data/${dataId}/delete`);
      if (res.data.success) {
        alert('删除成功！');
        loadData();
      } else {
        alert('删除失败: ' + (res.data.error || '未知错误'));
      }
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleBatchUpload = async () => {
    if (!batchData.trim()) {
      setError('请输入要上传的数据');
      return;
    }

    try {
      const dataArray = JSON.parse(batchData);
      if (!Array.isArray(dataArray)) {
        setError('数据格式错误，应为JSON数组');
        return;
      }

      const res = await axios.post(`${API_BASE_URL}/environment/data/batch-upload`, dataArray);
      if (res.data.success) {
        alert(res.data.message);
        setShowBatchModal(false);
        setBatchData('');
        loadData();
      } else {
        setError(res.data.error || res.data.message || '上传失败');
      }
    } catch (error) {
      console.error('批量上传失败:', error);
      if (error.response?.data?.errors) {
        setError(`上传失败: ${error.response.data.errors.join('; ')}`);
      } else {
        setError('数据格式错误或解析失败，请检查JSON格式');
      }
    }
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  const resetFilters = () => {
    setFilters({
      region_id: '',
      indicator_id: '',
      start_date: '',
      end_date: ''
    });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  return (
    <div className="data-management">
      <div className="section-header">
        <h2>环境监测数据管理</h2>
        <div className="controls">
          <button onClick={loadData} className="btn-refresh">
            刷新列表
          </button>
          <button onClick={handleAddData} className="btn-action">
            新增数据
          </button>
          <button onClick={() => setShowBatchModal(true)} className="btn-action">
            批量上传
          </button>
        </div>
      </div>

      {/* 过滤器 */}
      <div className="filters" style={{
        backgroundColor: 'white',
        padding: '15px',
        borderRadius: '8px',
        marginBottom: '20px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem' }}>区域</label>
            <select
              name="region_id"
              value={filters.region_id}
              onChange={handleFilterChange}
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
            >
              <option value="">全部区域</option>
              {regions.map(region => (
                <option key={region.region_id} value={region.region_id}>
                  {region.region_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem' }}>监测指标</label>
            <select
              name="indicator_id"
              value={filters.indicator_id}
              onChange={handleFilterChange}
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
            >
              <option value="">全部指标</option>
              {indicators.map(indicator => (
                <option key={indicator.indicator_id} value={indicator.indicator_id}>
                  {indicator.indicator_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem' }}>开始日期</label>
            <input
              type="date"
              name="start_date"
              value={filters.start_date}
              onChange={handleFilterChange}
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem' }}>结束日期</label>
            <input
              type="date"
              name="end_date"
              value={filters.end_date}
              onChange={handleFilterChange}
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
            />
          </div>
        </div>

        <div style={{ marginTop: '15px', display: 'flex', justifyContent: 'space-between' }}>
          <button
            onClick={resetFilters}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            重置筛选
          </button>
          <div style={{ fontSize: '0.9rem', color: '#666' }}>
            共 {pagination.total} 条记录，第 {pagination.page} / {pagination.pages} 页
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>数据编号</th>
                  <th>监测时间</th>
                  <th>指标</th>
                  <th>监测值</th>
                  <th>区域</th>
                  <th>设备</th>
                  <th>状态</th>
                  <th>数据质量</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {dataList.length > 0 ? dataList.map((data) => (
                  <tr key={data.data_id} className={data.is_abnormal ? 'abnormal-row' : ''}>
                    <td>{data.data_id}</td>
                    <td>{new Date(data.collection_time).toLocaleString()}</td>
                    <td>{data.indicator_name}</td>
                    <td>{data.monitor_value}</td>
                    <td>{data.region_name}</td>
                    <td>{data.device_type}</td>
                    <td>
                      <span className={`status-badge ${data.is_abnormal ? 'status-error' : 'status-success'}`}>
                        {data.is_abnormal ? '异常' : '正常'}
                      </span>
                    </td>
                    <td>
                      <span className={`quality-badge quality-${data.data_quality}`}>
                        {data.data_quality}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleEditData(data)}
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
                          onClick={() => handleDeleteData(data.data_id)}
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
                    <td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>
                      暂无环境监测数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* 分页控件 */}
          {pagination.pages > 1 && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              marginTop: '20px',
              gap: '5px'
            }}>
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page <= 1}
                style={{
                  padding: '5px 10px',
                  backgroundColor: pagination.page > 1 ? '#2a5298' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: pagination.page > 1 ? 'pointer' : 'not-allowed'
                }}
              >
                上一页
              </button>

              {[...Array(pagination.pages).keys()].map(i => (
                <button
                  key={i + 1}
                  onClick={() => handlePageChange(i + 1)}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: pagination.page === i + 1 ? '#28a745' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  {i + 1}
                </button>
              ))}

              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page >= pagination.pages}
                style={{
                  padding: '5px 10px',
                  backgroundColor: pagination.page < pagination.pages ? '#2a5298' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: pagination.page < pagination.pages ? 'pointer' : 'not-allowed'
                }}
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}

      {/* 单条数据模态框 */}
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
              {editingData ? '编辑环境监测数据' : '新增环境监测数据'}
            </h3>

            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  监测指标 *
                </label>
                <select
                  name="indicator_id"
                  value={formData.indicator_id}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                >
                  <option value="">请选择监测指标</option>
                  {indicators.map(indicator => (
                    <option key={indicator.indicator_id} value={indicator.indicator_id}>
                      {indicator.indicator_name} ({indicator.indicator_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  监测设备 *
                </label>
                <select
                  name="device_id"
                  value={formData.device_id}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                >
                  <option value="">请选择监测设备</option>
                  {devices.map(device => (
                    <option key={device.device_id} value={device.device_id}>
                      {device.device_type} ({device.device_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  区域 *
                </label>
                <select
                  name="region_id"
                  value={formData.region_id}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                >
                  <option value="">请选择区域</option>
                  {regions.map(region => (
                    <option key={region.region_id} value={region.region_id}>
                      {region.region_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  监测值 *
                </label>
                <input
                  type="number"
                  step="0.0001"
                  name="monitor_value"
                  value={formData.monitor_value}
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
                  数据质量
                </label>
                <select
                  name="data_quality"
                  value={formData.data_quality}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="优">优</option>
                  <option value="良">良</option>
                  <option value="中">中</option>
                  <option value="差">差</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  采集时间
                </label>
                <input
                  type="datetime-local"
                  name="collection_time"
                  value={formData.collection_time}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
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
                  onClick={() => setShowModal(false)}
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
                  {editingData ? '更新' : '新增'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 批量上传模态框 */}
      {showBatchModal && (
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
            width: '600px',
            maxWidth: '90%',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <h3 style={{ marginBottom: '20px' }}>批量上传环境监测数据</h3>

            <div style={{ marginBottom: '15px' }}>
              <p style={{ marginBottom: '10px' }}>
                请输入JSON格式的监测数据数组，每条数据应包含以下字段：
              </p>
              <ul style={{ marginBottom: '10px', paddingLeft: '20px' }}>
                <li>indicator_id (监测指标编号)</li>
                <li>device_id (监测设备编号)</li>
                <li>region_id (区域编号)</li>
                <li>monitor_value (监测值)</li>
                <li>data_quality (可选，数据质量)</li>
                <li>collection_time (可选，采集时间)</li>
              </ul>
            </div>

            <div className="form-group" style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                监测数据 (JSON数组)
              </label>
              <textarea
                value={batchData}
                onChange={(e) => setBatchData(e.target.value)}
                style={{
                  width: '100%',
                  height: '300px',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontSize: '0.9rem'
                }}
                placeholder={`
示例:
[
  {
    "indicator_id": "I001",
    "device_id": "D001",
    "region_id": "R001",
    "monitor_value": 25.5,
    "data_quality": "优",
    "collection_time": "2024-01-15 10:30:00"
  },
  {
    "indicator_id": "I002",
    "device_id": "D002",
    "region_id": "R002",
    "monitor_value": 7.2,
    "data_quality": "良"
  }
]
                `}
              />
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
                onClick={() => {
                  setShowBatchModal(false);
                  setBatchData('');
                  setError('');
                }}
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
                onClick={handleBatchUpload}
                style={{
                  padding: '8px 20px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                上传
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnvironmentDataManagement;
