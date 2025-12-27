// src/components/DeviceManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://192.168.69.97:5001/api';

const DeviceManagement = ({ onDeviceUpdate }) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [deviceTypes, setDeviceTypes] = useState([]);
  const [regions, setRegions] = useState([]);
  const [formData, setFormData] = useState({
    device_id: '',
    device_type: '',
    region_id: '',
    install_time: new Date().toISOString().split('T')[0],
    calibration_cycle: '30天',
    operation_status: '正常',
    comm_proto: 'HTTP'
  });
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [realTimeUpdates, setRealTimeUpdates] = useState(true);

  useEffect(() => {
    loadDevices();
    loadDropdownData();

    // 启动实时更新
    if (realTimeUpdates) {
      const interval = setInterval(() => {
        loadDevices();
      }, 30000); // 每30秒更新一次

      return () => clearInterval(interval);
    }
  }, [realTimeUpdates]);

  const loadDevices = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/devices/all`);
      if (res.data.success) {
        setDevices(res.data.devices || []);
      }
    } catch (error) {
      console.error('加载监测设备失败:', error);
      setError('加载失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadDropdownData = async () => {
    try {
      // 加载设备类型
      const typesRes = await axios.get(`${API_BASE_URL}/devices/types`);
      if (typesRes.data.success) {
        setDeviceTypes(typesRes.data.device_types || []);
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

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleAddDevice = () => {
    setEditingDevice(null);
    setFormData({
      device_id: '',
      device_type: deviceTypes[0] || '',
      region_id: regions[0]?.region_id || '',
      install_time: new Date().toISOString().split('T')[0],
      calibration_cycle: '30天',
      operation_status: '正常',
      comm_proto: 'HTTP'
    });
    setShowModal(true);
    setError('');
  };

  const handleEditDevice = (device) => {
    setEditingDevice(device);
    setFormData({
      device_id: device.device_id,
      device_type: device.device_type,
      region_id: device.region_id,
      install_time: device.install_time ?
        new Date(device.install_time).toISOString().split('T')[0] :
        new Date().toISOString().split('T')[0],
      calibration_cycle: device.calibration_cycle || '30天',
      operation_status: device.operation_status || '正常',
      comm_proto: device.comm_proto || 'HTTP'
    });
    setShowModal(true);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (editingDevice) {
        // 更新设备
        const res = await axios.put(
          `${API_BASE_URL}/devices/${editingDevice.device_id}/update`,
          formData
        );
        if (res.data.success) {
          alert('更新成功！');
          setShowModal(false);
          loadDevices();
          if (onDeviceUpdate) onDeviceUpdate();
        } else {
          setError(res.data.error || '更新失败');
        }
      } else {
        // 新增设备 - 移除 last_maintenance 字段
        const deviceData = {
          device_id: formData.device_id,
          device_type: formData.device_type,
          region_id: formData.region_id,
          install_time: formData.install_time,
          calibration_cycle: formData.calibration_cycle,
          operation_status: formData.operation_status,
          comm_proto: formData.comm_proto
        };

        const res = await axios.post(`${API_BASE_URL}/devices/add`, deviceData);
        if (res.data.success) {
          alert('新增成功！');
          setShowModal(false);
          loadDevices();
          if (onDeviceUpdate) onDeviceUpdate();
        } else {
          setError(res.data.error || '新增失败');
        }
      }
    } catch (error) {
      console.error('提交失败:', error);
      setError('提交失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    if (!window.confirm('确定要删除该监测设备吗？删除后相关数据将无法关联设备。')) {
      return;
    }

    try {
      const res = await axios.delete(`${API_BASE_URL}/devices/${deviceId}/delete`);
      if (res.data.success) {
        alert('删除成功！');
        loadDevices();
        if (onDeviceUpdate) onDeviceUpdate();
      } else {
        alert('删除失败: ' + (res.data.error || '未知错误'));
      }
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleUpdateStatus = async (deviceId, status) => {
    try {
      const res = await axios.put(`${API_BASE_URL}/devices/${deviceId}/status`, {
        status: status
      });
      if (res.data.success) {
        alert(`设备状态已更新为: ${status}`);
        loadDevices();
        if (onDeviceUpdate) onDeviceUpdate();

        // 如果是将设备状态设置为正常，尝试清除该设备的警报
        if (status === '正常') {
          try {
            await axios.post(`${API_BASE_URL}/alerts/clear`, {
              alert_key: `device_fault_${deviceId}`
            });
          } catch (error) {
            // 清除警报失败不影响主要操作
            console.log('清除警报失败:', error);
          }
        }
      } else {
        alert('状态更新失败: ' + (res.data.error || '未知错误'));
      }
    } catch (error) {
      console.error('状态更新失败:', error);
      alert('状态更新失败: ' + (error.response?.data?.error || error.message));
    }
  };

  // 筛选设备
  const filteredDevices = devices.filter(device =>
    device.device_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    device.device_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (device.region_name && device.region_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // 设备状态统计
  const statusStats = {
    total: devices.length,
    normal: devices.filter(d => d.operation_status === '正常').length,
    fault: devices.filter(d => d.operation_status === '故障').length,
    offline: devices.filter(d => d.operation_status === '离线').length
  };

  return (
    <div className="data-management">
      <div className="section-header">
        <h2>监测设备管理</h2>
        <div className="controls">
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="搜索设备ID、类型或区域..."
              value={searchTerm}
              onChange={handleSearchChange}
              style={{
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                width: '300px'
              }}
            />
            <button onClick={loadDevices} className="btn-refresh">
              手动刷新
            </button>
            <button onClick={handleAddDevice} className="btn-action">
              新增设备
            </button>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={realTimeUpdates}
                onChange={(e) => setRealTimeUpdates(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              <span style={{ fontSize: '0.9rem' }}>实时更新</span>
            </label>
          </div>
        </div>
      </div>

      {/* 设备状态统计 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '20px'
      }}>
        <div style={{
          backgroundColor: '#28a745',
          color: 'white',
          padding: '15px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>正常设备</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{statusStats.normal}</div>
          <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
            {statusStats.total > 0 ? ((statusStats.normal / statusStats.total * 100).toFixed(1) + '%') : '0%'}
          </div>
        </div>

        <div style={{
          backgroundColor: '#dc3545',
          color: 'white',
          padding: '15px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>故障设备</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{statusStats.fault}</div>
          <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
            {statusStats.total > 0 ? ((statusStats.fault / statusStats.total * 100).toFixed(1) + '%') : '0%'}
          </div>
        </div>

        <div style={{
          backgroundColor: '#ffc107',
          color: '#333',
          padding: '15px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>离线设备</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{statusStats.offline}</div>
          <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
            {statusStats.total > 0 ? ((statusStats.offline / statusStats.total * 100).toFixed(1) + '%') : '0%'}
          </div>
        </div>

        <div style={{
          backgroundColor: '#007bff',
          color: 'white',
          padding: '15px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>设备总数</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{statusStats.total}</div>
          <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>当前在线管理</div>
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
                  <th>设备编号</th>
                  <th>设备类型</th>
                  <th>区域</th>
                  <th>安装时间</th>
                  <th>校准周期</th>
                  <th>运行状态</th>
                  <th>通信协议</th>
                  <th>最后更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredDevices.length > 0 ? filteredDevices.map((device) => (
                  <tr key={device.device_id} className={
                    device.operation_status === '故障' ? 'abnormal-row' :
                    device.operation_status === '离线' ? 'warning-row' : ''
                  }>
                    <td>{device.device_id}</td>
                    <td>{device.device_type}</td>
                    <td>{device.region_name}</td>
                    <td>{device.install_time ? new Date(device.install_time).toLocaleDateString() : '-'}</td>
                    <td>{device.calibration_cycle || '-'}</td>
                    <td>
                      <span className={`status-badge status-${device.operation_status}`}>
                        {device.operation_status}
                      </span>
                    </td>
                    <td>{device.comm_proto || '-'}</td>
                    <td>{device.status_update_time ?
                      new Date(device.status_update_time).toLocaleString() : '-'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                          onClick={() => handleEditDevice(device)}
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
                          onClick={() => handleDeleteDevice(device.device_id)}
                          className="btn-action"
                          style={{
                            backgroundColor: '#dc3545',
                            padding: '4px 10px',
                            fontSize: '0.85rem'
                          }}
                        >
                          删除
                        </button>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                          <button
                            onClick={() => handleUpdateStatus(device.device_id, '正常')}
                            className="btn-action"
                            style={{
                              backgroundColor: device.operation_status === '正常' ? '#28a745' : '#6c757d',
                              padding: '2px 6px',
                              fontSize: '0.75rem'
                            }}
                          >
                            正常
                          </button>
                          <button
                            onClick={() => handleUpdateStatus(device.device_id, '故障')}
                            className="btn-action"
                            style={{
                              backgroundColor: device.operation_status === '故障' ? '#dc3545' : '#6c757d',
                              padding: '2px 6px',
                              fontSize: '0.75rem'
                            }}
                          >
                            故障
                          </button>
                          <button
                            onClick={() => handleUpdateStatus(device.device_id, '离线')}
                            className="btn-action"
                            style={{
                              backgroundColor: device.operation_status === '离线' ? '#ffc107' : '#6c757d',
                              color: '#333',
                              padding: '2px 6px',
                              fontSize: '0.75rem'
                            }}
                          >
                            离线
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>
                      {searchTerm ? '未找到匹配的设备' : '暂无监测设备数据'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {filteredDevices.length > 0 && (
            <div style={{
              textAlign: 'center',
              padding: '10px',
              color: '#666',
              fontSize: '0.9rem',
              borderTop: '1px solid #eee',
              marginTop: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                显示 {filteredDevices.length} 个设备{searchTerm && ` (搜索: "${searchTerm}")`}
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <span>最后更新: {new Date().toLocaleTimeString()}</span>
                {realTimeUpdates && (
                  <span style={{
                    backgroundColor: '#28a745',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '0.8rem'
                  }}>
                    实时更新中
                  </span>
                )}
              </div>
            </div>
          )}
        </>
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
              {editingDevice ? '编辑监测设备' : '新增监测设备'}
            </h3>

            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  设备编号 *
                </label>
                <input
                  type="text"
                  name="device_id"
                  value={formData.device_id}
                  onChange={handleInputChange}
                  disabled={editingDevice}
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
                  设备类型 *
                </label>
                <select
                  name="device_type"
                  value={formData.device_type}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                  required
                >
                  <option value="">请选择设备类型</option>
                  {deviceTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  部署区域 *
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
                  <option value="">请选择部署区域</option>
                  {regions.map(region => (
                    <option key={region.region_id} value={region.region_id}>
                      {region.region_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  安装时间
                </label>
                <input
                  type="date"
                  name="install_time"
                  value={formData.install_time}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  校准周期
                </label>
                <select
                  name="calibration_cycle"
                  value={formData.calibration_cycle}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="">未设置</option>
                  <option value="7天">7天</option>
                  <option value="15天">15天</option>
                  <option value="30天">30天</option>
                  <option value="60天">60天</option>
                  <option value="90天">90天</option>
                  <option value="180天">180天</option>
                  <option value="365天">365天</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  运行状态
                </label>
                <select
                  name="operation_status"
                  value={formData.operation_status}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="正常">正常</option>
                  <option value="故障">故障</option>
                  <option value="离线">离线</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                  通信协议
                </label>
                <select
                  name="comm_proto"
                  value={formData.comm_proto}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="HTTP">HTTP</option>
                  <option value="MQTT">MQTT</option>
                  <option value="LoRa">LoRa</option>
                  <option value="NB-IoT">NB-IoT</option>
                  <option value="CoAP">CoAP</option>
                  <option value="Modbus">Modbus</option>
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
                  {editingDevice ? '更新' : '新增'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeviceManagement;