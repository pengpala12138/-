// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// 导入新增的管理组件
import IndicatorManagement from './components/IndicatorManagement';
import EnvironmentDataManagement from './components/EnvironmentDataManagement';
import DeviceManagement from './components/DeviceManagement';

const API_BASE_URL = 'http://192.168.69.97:5001/api';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [recentData, setRecentData] = useState([]);
  const [abnormalData, setAbnormalData] = useState([]);
  const [deviceSummary, setDeviceSummary] = useState([]);
  const [devicesNeedCalibration, setDevicesNeedCalibration] = useState([]);
  const [allDevices, setAllDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dashboardStats, setDashboardStats] = useState({
    total_devices: 0,
    normal_devices: 0,
    need_calibration: 0,
    total_data_count: 0,
    total_abnormal_count: 0,
    recent_data_total: 0,
    recent_abnormal_count: 0
  });
  const [calibrationModal, setCalibrationModal] = useState({
    show: false,
    deviceId: null,
    deviceName: '',
    currentStatus: ''
  });
  const [deviceAlerts, setDeviceAlerts] = useState([]);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [currentAlert, setCurrentAlert] = useState(null);
  const [showValueAdjustModal, setShowValueAdjustModal] = useState(false);
  const [adjustValue, setAdjustValue] = useState('');
  const [adjustData, setAdjustData] = useState(null);
  const [adjusting, setAdjusting] = useState(false);
  const [adjustThreshold, setAdjustThreshold] = useState({ lower: 0, upper: 0, unit: '' });
  const [shownAlertTimestamps, setShownAlertTimestamps] = useState({});

  useEffect(() => {
    loadDashboardData();
    startAutoRefresh();
    startAlertCheck();
  }, []);

  // 当标签页切换时重新加载数据
  useEffect(() => {
    if (activeTab === 'abnormal') {
      loadAbnormalData();
    }
  }, [activeTab]);

  // 自动刷新数据
  const startAutoRefresh = () => {
    // 每5分钟刷新一次数据
    setInterval(() => {
      loadDashboardData();
    }, 5 * 60 * 1000);
  };

  // 检查设备警报
  const startAlertCheck = () => {
    // 每30秒检查一次警报
    setInterval(() => {
      checkDeviceAlerts();
    }, 30 * 1000);
  };

  const checkDeviceAlerts = async () => {
    try {
      // 获取所有设备状态
      const devicesRes = await axios.get(`${API_BASE_URL}/devices/all`);
      const devices = devicesRes.data.success ? devicesRes.data.devices : [];

      // 检查警报
      const res = await axios.get(`${API_BASE_URL}/alerts/device`);
      if (res.data.success && res.data.alerts.length > 0) {
        // 过滤掉故障设备的数据异常警报
        const filteredAlertsRaw = res.data.alerts.filter(alert => {
          // 如果是数据异常警报，检查设备状态
          if (alert.alert_type === 'data_abnormal') {
            const device = devices.find(d => d.device_id === alert.device_id);
            // 只显示正常设备的数据异常警报
            return device && device.operation_status === '正常';
          }
          // 设备故障警报始终显示
          return true;
        });

        // 仅对数据异常预警做30分钟不重复弹窗
        const now = Date.now();
        const thirtyMinMs = 30 * 60 * 1000;
        const buildKey = (a) => `data_abnormal_${a.device_id}_${a.indicator_id}`;
        const filteredAlerts = filteredAlertsRaw.filter(a => {
          if (a.alert_type !== 'data_abnormal') return true;
          const key = buildKey(a);
          const lastShown = shownAlertTimestamps[key];
          return !(lastShown && (now - lastShown < thirtyMinMs));
        });

        setDeviceAlerts(filteredAlertsRaw);

        // 如果有新警报且没有显示警报弹窗，显示第一个警报
        if (!showAlertModal && filteredAlerts.length > 0) {
          const newAlert = filteredAlerts[0];
          setCurrentAlert(newAlert);
          setShowAlertModal(true);
          if (newAlert.alert_type === 'data_abnormal') {
            const key = buildKey(newAlert);
            setShownAlertTimestamps(prev => ({ ...prev, [key]: now }));
          }
        }
      } else {
        setDeviceAlerts([]);
      }
    } catch (error) {
      console.error('检查设备警报失败:', error);
    }
  };

  // 在 loadAbnormalData 中添加调试
const loadAbnormalData = async () => {
  try {
    console.log('开始加载异常数据...');
    const abnormalRes = await axios.get(`${API_BASE_URL}/environment/data/abnormal`);
    if (abnormalRes.data.success) {
      console.log('异常数据加载成功，数量:', abnormalRes.data.data?.length);
      setAbnormalData(abnormalRes.data.data || []);
    }
  } catch (error) {
    console.error('加载异常数据失败:', error);
  }
};

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // 获取仪表盘统计
      const statsRes = await axios.get(`${API_BASE_URL}/stats/dashboard`);
      if (statsRes.data.success) {
        setDashboardStats(prev => ({
          ...prev,
          ...statsRes.data.stats
        }));
      }

      // 获取数据总数
      try {
        const countRes = await axios.get(`${API_BASE_URL}/environment/data/count`);
        if (countRes.data.success) {
          setDashboardStats(prev => ({
            ...prev,
            total_data_count: countRes.data.count || 0
          }));
        }
      } catch (error) {
        console.error('获取数据总数失败:', error);
      }

      // 获取异常数据总数
      try {
        const abnormalCountRes = await axios.get(`${API_BASE_URL}/environment/data/abnormal-count`);
        if (abnormalCountRes.data.success) {
          setDashboardStats(prev => ({
            ...prev,
            total_abnormal_count: abnormalCountRes.data.count || 0
          }));
        }
      } catch (error) {
        console.error('获取异常数据总数失败:', error);
        // 如果API不存在，可以计算异常数据长度
        const abnormalRes = await axios.get(`${API_BASE_URL}/environment/data/abnormal`);
        if (abnormalRes.data.success) {
          setDashboardStats(prev => ({
            ...prev,
            total_abnormal_count: abnormalRes.data.data?.length || 0
          }));
          setAbnormalData(abnormalRes.data.data || []);
        }
      }

      // 获取最近15天数据
      const recentRes = await axios.get(`${API_BASE_URL}/environment/data/recent?days=15`);
      if (recentRes.data.success) {
        const recentDataList = recentRes.data.data || [];
        setRecentData(recentDataList);

        // 计算近期数据的异常数量和异常率
        const recentAbnormalCount = recentDataList.filter(data => data.is_abnormal).length;
        setDashboardStats(prev => ({
          ...prev,
          recent_data_total: recentDataList.length,
          recent_abnormal_count: recentAbnormalCount
        }));
      }

      // 获取设备状态统计
      const deviceRes = await axios.get(`${API_BASE_URL}/devices/status-summary`);
      if (deviceRes.data.success) {
        setDeviceSummary(deviceRes.data.summary || []);
      }

      // 获取所有设备
      const allDevicesRes = await axios.get(`${API_BASE_URL}/devices/all`);
      if (allDevicesRes.data.success) {
        setAllDevices(allDevicesRes.data.devices || []);
      }

      // 获取需要校准的设备
      const calibrationRes = await axios.get(`${API_BASE_URL}/devices/need-calibration`);
      if (calibrationRes.data.success) {
        setDevicesNeedCalibration(calibrationRes.data.devices || []);
      }

    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 专门的表格数据刷新函数
  const refreshTableData = async () => {
    try {
      // 刷新最近数据
      const recentRes = await axios.get(`${API_BASE_URL}/environment/data/recent?days=15`);
      if (recentRes.data.success) {
        setRecentData(recentRes.data.data || []);
      }

      // 刷新异常数据
      const abnormalRes = await axios.get(`${API_BASE_URL}/environment/data/abnormal`);
      if (abnormalRes.data.success) {
        setAbnormalData(abnormalRes.data.data || []);
      }

      // 刷新设备数据
      const allDevicesRes = await axios.get(`${API_BASE_URL}/devices/all`);
      if (allDevicesRes.data.success) {
        setAllDevices(allDevicesRes.data.devices || []);
      }

      console.log('表格数据已刷新');
    } catch (error) {
      console.error('刷新表格数据失败:', error);
    }
  };

  const showCalibrationModal = (deviceId, deviceName, currentStatus) => {
    setCalibrationModal({
      show: true,
      deviceId,
      deviceName,
      currentStatus
    });
  };

  const closeCalibrationModal = () => {
    setCalibrationModal({
      show: false,
      deviceId: null,
      deviceName: '',
      currentStatus: ''
    });
  };

  // 清除警报的辅助函数
  const handleAlertClear = async (alert) => {
    const alertType = alert.alert_type;
    const deviceId = alert.device_id;

    let alertKey;
    if (alertType === 'device_fault') {
      alertKey = `device_fault_${deviceId}`;
    } else if (alertType === 'data_abnormal') {
      alertKey = `data_abnormal_${deviceId}_${alert.indicator_id}`;
    }

    if (alertKey) {
      await axios.post(`${API_BASE_URL}/alerts/clear`, {
        alert_key: alertKey
      });
    }
  };

  // 调整监测值的方法
 // 优化的调整监测值方法
const handleValueAdjust = async () => {
  if (!adjustValue || adjustValue === '') {
    alert('请输入监测值');
    return;
  }

  const newValue = parseFloat(adjustValue);

  if (isNaN(newValue)) {
    alert('请输入有效的数字');
    return;
  }

  const thresholdLower = adjustThreshold.lower;
  const thresholdUpper = adjustThreshold.upper;

  if (newValue < thresholdLower || newValue > thresholdUpper) {
    alert(`新值 ${newValue} 超出阈值范围 [${thresholdLower}, ${thresholdUpper}]`);
    return;
  }

  setAdjusting(true);

  try {
    let updatePromise;

    // 如果有具体数据ID，直接更新
    if (adjustData && adjustData.data_id) {
      updatePromise = axios.put(
        `${API_BASE_URL}/environment/data/${adjustData.data_id}/adjust`,
        { monitor_value: newValue }
      );
    } else if (currentAlert) {
      // 如果没有数据ID，但知道设备ID和指标ID，查找并更新
      const findRes = await axios.get(`${API_BASE_URL}/environment/data/recent`, {
        params: {
          days: 1,
          device_id: currentAlert.device_id,
          indicator_id: currentAlert.indicator_id,
          limit: 1
        }
      });

      if (findRes.data.success && findRes.data.data.length > 0) {
        const latestData = findRes.data.data[0];
        updatePromise = axios.put(
          `${API_BASE_URL}/environment/data/${latestData.data_id}/adjust`,
          { monitor_value: newValue }
        );
      }
    }

    if (updatePromise) {
      const res = await updatePromise;

      if (res.data.success) {
        // 快速清除当前警报
        setDeviceAlerts(prev => prev.filter(alert =>
          !(alert.device_id === currentAlert?.device_id &&
            alert.indicator_id === currentAlert?.indicator_id)
        ));

        // 立即更新本地数据状态
        if (activeTab === 'abnormal') {
          setAbnormalData(prev => prev.filter(data =>
            !(data.device_id === currentAlert?.device_id &&
              data.indicator_id === currentAlert?.indicator_id &&
              data.monitor_value === currentAlert?.value)
          ));
        }

        // 延迟更新仪表盘数据，让用户先看到响应
        setTimeout(() => {
          refreshAllData();
        }, 300);

        alert(`✅ 监测值已更新为 ${newValue}`);
      }
    }

    // 快速关闭弹窗
    setShowValueAdjustModal(false);
    setShowAlertModal(false);
    setCurrentAlert(null);
    setAdjustValue('');

  } catch (error) {
    console.error('调整失败:', error);
    alert('调整失败: ' + (error.response?.data?.error || error.message));
  } finally {
    setAdjusting(false);
  }
};

  // 优化后的 handleAlertAction 函数
const handleAlertAction = async (action) => {
  try {
    if (action === 'adjust' && currentAlert) {
      // 直接从当前警报信息获取阈值，不调用额外API
      const thresholdLower = currentAlert.threshold_lower || 0;
      const thresholdUpper = currentAlert.threshold_upper || 100;
      const unit = currentAlert.unit || '';

      // 设置调整值（如果有当前值，使用当前值，否则使用阈值中间值）
      const currentValue = currentAlert.value || ((thresholdLower + thresholdUpper) / 2).toFixed(2);

      // 直接从警报中获取信息，不调用额外API
      setAdjustData({
        device_id: currentAlert.device_id,
        indicator_id: currentAlert.indicator_id,
        value: currentValue
      });

      setAdjustValue(currentValue);
      setAdjustThreshold({
        lower: thresholdLower,
        upper: thresholdUpper,
        unit: unit
      });

      setShowValueAdjustModal(true);
      setShowAlertModal(false);
      return;
    }

    if (action === 'clear' && currentAlert) {
      // 简化的清除逻辑
      const alertType = currentAlert.alert_type;
      const deviceId = currentAlert.device_id;

      try {
        if (alertType === 'device_fault') {
          // 直接调用设备状态更新，不等待关联数据
          await axios.put(`${API_BASE_URL}/devices/${deviceId}/status`, {
            status: '正常'
          });
        }

        // 清除警报（快速处理）
        const clearRes = await axios.post(`${API_BASE_URL}/alerts/clear`, {
          alert_key: `device_fault_${deviceId}`
        });

        if (clearRes.data.success) {
          // 快速更新本地状态，不等待完整刷新
          setDeviceAlerts(prev => prev.filter(alert =>
            !(alert.device_id === deviceId && alert.alert_type === alertType)
          ));
        }

      } catch (error) {
        console.error('快速清除警报失败:', error);
      }

      // 延迟刷新数据，让用户先看到响应
      setTimeout(() => {
        refreshAllData();
      }, 100);

      setShowAlertModal(false);
      setCurrentAlert(null);
    } else if (action === 'ignore') {
      setShowAlertModal(false);
      setCurrentAlert(null);
    }
  } catch (error) {
    console.error('处理警报失败:', error);
    alert('处理警报失败: ' + (error.response?.data?.error || error.message));
    setShowAlertModal(false);
    setCurrentAlert(null);
  }
};

  const handleMarkCalibrated = async (deviceId, calibrationResult, calibrationDate = null) => {
    try {
      const data = {
        calibration_result: calibrationResult
      };

      if (calibrationDate) {
        data.calibration_date = calibrationDate;
      }

      const res = await axios.put(`${API_BASE_URL}/devices/${deviceId}/calibration`, data);

      if (res.data.success) {
        const resultText = calibrationResult === '合格' ? '校准合格' : '校准不合格';
        alert(`设备 ${deviceId} ${resultText}`);

        // 重新加载数据
        setTimeout(() => {
          loadDashboardData();
        }, 500);
      } else {
        alert(`校准失败: ${res.data.error}`);
      }
    } catch (error) {
      console.error('标记校准失败:', error);
      alert('标记校准失败');
    } finally {
      closeCalibrationModal();
    }
  };

  const handleMarkUncalibrated = async (deviceId) => {
    try {
      // 设置一个很久以前的校准日期，让设备显示为需要校准
      const oldDate = '2023-01-01'; // 设置一个过去很久的日期
      const res = await axios.put(`${API_BASE_URL}/devices/${deviceId}/calibration`, {
        calibration_result: '合格',
        calibration_date: oldDate
      });

      if (res.data.success) {
        alert(`设备 ${deviceId} 已标记为未校准`);
        // 重新加载数据
        setTimeout(() => {
          loadDashboardData();
        }, 500);
      } else {
        alert(`标记未校准失败: ${res.data.error}`);
      }
    } catch (error) {
      console.error('标记未校准失败:', error);
      alert('标记未校准失败');
    }
  };

  const handleUpdateDeviceStatus = async (deviceId, status) => {
    try {
      const res = await axios.put(`${API_BASE_URL}/devices/${deviceId}/status`, {
        status: status
      });

      if (res.data.success) {
        alert(`设备状态更新成功: ${res.data.old_status} -> ${res.data.new_status}`);
        // 重新加载数据
        setTimeout(() => {
          loadDashboardData();
        }, 500);
      } else {
        alert(`更新失败: ${res.data.error}`);
      }
    } catch (error) {
      console.error('更新设备状态失败:', error);
      alert(`更新设备状态失败: ${error.response?.data?.error || error.message}`);
    }
  };

  const handleUploadTestData = async () => {
    try {
      const testData = {
        indicator_id: 'I001',
        device_id: 'D001',
        collection_time: new Date().toISOString().slice(0, 19).replace('T', ' '),
        monitor_value: Math.random() * 50,
        data_quality: '优'
      };

      const res = await axios.post(`${API_BASE_URL}/environment/data/upload`, testData);
      if (res.data.success) {
        alert(`数据上传成功！数据ID: ${res.data.data_id}`);
        loadDashboardData();
        await checkDeviceAlerts();
      } else {
        alert(`上传失败: ${res.data.error}`);
      }
    } catch (error) {
      console.error('上传测试数据失败:', error);
      alert('上传失败');
    }
  };

  // 刷新异常数据（当指标阈值修改后调用）
  const refreshAbnormalData = async (forceRecalc = false) => {
    try {
      let affectedCount = 0;

      // 如果需要强制重新计算，调用后端API
      if (forceRecalc) {
        const recalcRes = await axios.post(`${API_BASE_URL}/environment/data/recalculate-abnormal`);
        if (recalcRes.data.success) {
          affectedCount = recalcRes.data.affected || 0;
          alert(`异常数据重新计算完成！异常数据总数为：${affectedCount}条`);
        }
      }

      // 重新加载异常数据
      const abnormalRes = await axios.get(`${API_BASE_URL}/environment/data/abnormal`);
      if (abnormalRes.data.success) {
        setAbnormalData(abnormalRes.data.data || []);
        // 更新异常数据总数
        setDashboardStats(prev => ({
          ...prev,
          total_abnormal_count: abnormalRes.data.data?.length || 0
        }));
      }

      // 重新加载仪表盘统计
      const statsRes = await axios.get(`${API_BASE_URL}/stats/dashboard`);
      if (statsRes.data.success) {
        setDashboardStats(prev => ({
          ...prev,
          ...statsRes.data.stats
        }));
      }

      // 重新加载最近数据
      const recentRes = await axios.get(`${API_BASE_URL}/environment/data/recent?days=15`);
      if (recentRes.data.success) {
        const recentDataList = recentRes.data.data || [];
        setRecentData(recentDataList);

        // 计算近期数据的异常数量和异常率
        const recentAbnormalCount = recentDataList.filter(data => data.is_abnormal).length;
        setDashboardStats(prev => ({
          ...prev,
          recent_data_total: recentDataList.length,
          recent_abnormal_count: recentAbnormalCount
        }));
      }

      if (!forceRecalc) {
        alert('异常数据已刷新！');
      }
      await checkDeviceAlerts();
    } catch (error) {
      console.error('刷新异常数据失败:', error);
      alert('刷新失败: ' + (error.message || '未知错误'));
    }
  };

  // 刷新所有数据
const refreshAllData = async () => {
  setLoading(true);
  try {
    console.log('开始刷新所有数据...');

    // 1. 刷新仪表盘数据
    await loadDashboardData();

    // 2. 刷新异常数据
    await loadAbnormalData();

    // 3. 刷新最近数据
    const recentRes = await axios.get(`${API_BASE_URL}/environment/data/recent?days=15`);
    if (recentRes.data.success) {
      setRecentData(recentRes.data.data || []);
    }

    // 4. 刷新设备数据
    const allDevicesRes = await axios.get(`${API_BASE_URL}/devices/all`);
    if (allDevicesRes.data.success) {
      setAllDevices(allDevicesRes.data.devices || []);
    }

    // 5. 刷新需要校准的设备
    const calibrationRes = await axios.get(`${API_BASE_URL}/devices/need-calibration`);
    if (calibrationRes.data.success) {
      setDevicesNeedCalibration(calibrationRes.data.devices || []);
    }

    console.log('所有数据刷新完成');

  } catch (error) {
    console.error('刷新数据失败:', error);
    alert('刷新失败: ' + error.message);
  } finally {
    setLoading(false);
  }
};
  const renderDashboard = () => {
    // 计算本页显示的数据统计
    const displayCount = Math.min(recentData.length, 15);
    const displayAbnormalCount = recentData.slice(0, displayCount).filter(data => data.is_abnormal).length;
    const displayAbnormalRate = displayCount > 0 ? (displayAbnormalCount / displayCount * 100).toFixed(1) : 0;

    // 计算近期数据（15天内）的异常率
    const recentAbnormalRate = dashboardStats.recent_data_total > 0
      ? ((dashboardStats.recent_abnormal_count / dashboardStats.recent_data_total) * 100).toFixed(1)
      : 0;

    // 计算总异常率
    const totalAbnormalRate = dashboardStats.total_data_count > 0
      ? ((dashboardStats.total_abnormal_count / dashboardStats.total_data_count) * 100).toFixed(1)
      : 0;

    return (
      <div className="dashboard">
        <div className="stats-grid">
          <div className="stat-card">
            <h3>设备总数</h3>
            <p className="stat-value">{dashboardStats.total_devices}</p>
          </div>
          <div className="stat-card">
            <h3>正常设备</h3>
            <p className="stat-value">{dashboardStats.normal_devices}</p>
          </div>
          <div className="stat-card">
            <h3>待校准设备</h3>
            <p className="stat-value">{dashboardStats.need_calibration}</p>
          </div>

          <div className="stat-card">
            <h3>监测数据总量</h3>
            <p className="stat-value">{dashboardStats.total_data_count}</p>
            <p className="stat-description">历史总数据</p>
          </div>

          <div className="stat-card">
            <h3>异常数据总数</h3>
            <p className="stat-value">{dashboardStats.total_abnormal_count}</p>
            <p className="stat-description">历史异常数据</p>
          </div>

          <div className="stat-card">
            <h3>总异常率</h3>
            <p className="stat-value">{totalAbnormalRate}%</p>
            <p className="stat-description">
              基于 {dashboardStats.total_data_count} 条数据
            </p>
          </div>
        </div>

        <div className="data-section">
          <div className="controls">
            <button onClick={refreshAllData} className="btn-refresh">
              刷新数据
            </button>
            <button onClick={handleUploadTestData} className="btn-test">
              生成测试数据
            </button>
            <button onClick={() => refreshAbnormalData(true)} className="btn-action" style={{backgroundColor: '#dc3545', color: 'white'}}>
              重新计算异常
            </button>
            <h2>最近监测数据（15天内）</h2>
          </div>

          {/* 统计数据 */}
          <div style={{
            backgroundColor: '#f8f9fa',
            padding: '15px',
            borderRadius: '6px',
            marginBottom: '15px',
            fontSize: '0.9rem',
            borderLeft: '4px solid #007bff'
          }}>
            <div style={{display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'center'}}>
              <div>
                <strong>📊 本页数据统计：</strong>
              </div>
              <div>
                显示数据：<strong>{displayCount}</strong> 条
              </div>
              <div>
                异常数据：<strong style={{color: '#dc3545'}}>
                  {displayAbnormalCount}
                </strong> 条
              </div>
              <div>
                本页异常率：<strong>{displayAbnormalRate}%</strong>
              </div>
            </div>

            <div style={{marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '20px', color: '#666'}}>
              <div>
                <strong>📈 近期数据统计（15天内）：</strong>
              </div>
              <div>
                总数据量：<strong>{dashboardStats.recent_data_total}</strong> 条
              </div>
              <div>
                异常数据：<strong style={{color: '#dc3545'}}>
                  {dashboardStats.recent_abnormal_count}
                </strong> 条
              </div>
              <div>
                近期异常率：<strong>{recentAbnormalRate}%</strong>
              </div>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>指标</th>
                  <th>监测值</th>
                  <th>区域</th>
                  <th>设备</th>
                  <th>状态</th>
                  <th>数据质量</th>
                </tr>
              </thead>
              <tbody>
                {recentData.length > 0 ? recentData.slice(0, 15).map((data, index) => (
                  <tr key={index} className={data.is_abnormal ? 'abnormal-row' : ''}>
                    <td>{new Date(data.collection_time).toLocaleString()}</td>
                    <td>{data.indicator_name || data.indicator_id}</td>
                    <td>
                      {data.monitor_value !== null && data.monitor_value !== undefined
                        ? `${data.monitor_value} ${data.unit || ''}`
                        : '无数据'}
                    </td>
                    <td>{data.region_name || data.region_id}</td>
                    <td>{data.device_type || data.device_id}</td>
                    <td>
                      <span className={`status-badge ${data.is_abnormal ? 'status-error' : 'status-success'}`}>
                        {data.is_abnormal ? '异常' : '正常'}
                      </span>
                    </td>
                    <td>
                      <span className={`quality-badge quality-${data.data_quality || '中'}`}>
                        {data.data_quality || '中'}
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="7" style={{textAlign: 'center', padding: '20px', color: '#666'}}>
                      <div style={{marginBottom: '10px'}}>暂无最近监测数据</div>
                      <button onClick={handleUploadTestData} className="btn-test" style={{padding: '8px 16px'}}>
                        生成测试数据
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            {recentData.length > 0 && (
              <div style={{textAlign: 'center', padding: '10px', color: '#666', fontSize: '0.9rem'}}>
                显示最近 {displayCount} 条数据，共 {recentData.length} 条
              </div>
            )}
          </div>
        </div>

        <div className="data-section">
          <h2>设备状态统计</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>区域</th>
                  <th>设备类型</th>
                  <th>总数</th>
                  <th>正常</th>
                  <th>故障</th>
                  <th>离线</th>
                  <th>正常率</th>
                </tr>
              </thead>
              <tbody>
                {deviceSummary.length > 0 ? deviceSummary.map((item, index) => (
                  <tr key={index}>
                    <td>{item.region_name}</td>
                    <td>{item.device_type}</td>
                    <td>{item.total_devices}</td>
                    <td>{item.normal_count}</td>
                    <td>{item.fault_count}</td>
                    <td>{item.offline_count}</td>
                    <td>{parseFloat(item.normal_rate || 0).toFixed(2)}%</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="7" style={{textAlign: 'center', padding: '20px'}}>
                      暂无设备统计数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const renderAbnormalData = () => (
    <div className="abnormal-data">
      <h2>异常数据监控</h2>
      <div className="controls">
        <button onClick={() => refreshAbnormalData(true)} className="btn-action" style={{backgroundColor: '#dc3545', color: 'white'}}>
          重新计算异常数据
        </button>
        <button onClick={() => refreshAbnormalData(false)} className="btn-refresh">
          刷新显示
        </button>
        <button onClick={handleUploadTestData} className="btn-test">
          生成测试数据
        </button>
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>区域</th>
              <th>指标</th>
              <th>监测值</th>
              <th>阈值范围</th>
              <th>设备</th>
              <th>异常原因</th>
              <th>数据质量</th>
            </tr>
          </thead>
          <tbody>
            {abnormalData.length > 0 ? abnormalData.map((data, index) => (
              <tr key={index} className="abnormal-row">
                <td>{new Date(data.collection_time).toLocaleString()}</td>
                <td>{data.region_name}</td>
                <td>{data.indicator_name}</td>
                <td className="value-highlight">{data.monitor_value}</td>
                <td>{data.standard_lower} - {data.standard_upper}</td>
                <td>{data.device_type}</td>
                <td className="error-text">{data.abnormal_reason}</td>
                <td>
                  <span className={`quality-badge quality-${data.data_quality}`}>
                    {data.data_quality}
                  </span>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="8" style={{textAlign: 'center', padding: '20px'}}>
                  暂无异常数据
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>国家公园生态环境监测系统</h1>
        <nav className="nav-tabs">
          <button
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            仪表盘
          </button>
          <button
            className={activeTab === 'abnormal' ? 'active' : ''}
            onClick={() => setActiveTab('abnormal')}
          >
            异常监控
          </button>
          <button
            className={activeTab === 'devices' ? 'active' : ''}
            onClick={() => setActiveTab('devices')}
          >
            设备管理
          </button>
          <button
            className={activeTab === 'indicators' ? 'active' : ''}
            onClick={() => setActiveTab('indicators')}
          >
            指标管理
          </button>
          <button
            className={activeTab === 'envData' ? 'active' : ''}
            onClick={() => setActiveTab('envData')}
          >
            数据管理
          </button>
        </nav>
      </header>

      <main className="app-main">
        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <>
            {activeTab === 'dashboard' && renderDashboard()}
            {activeTab === 'abnormal' && renderAbnormalData()}
            {activeTab === 'devices' && <DeviceManagement onDeviceUpdate={loadDashboardData} />}
            {activeTab === 'indicators' && <IndicatorManagement onIndicatorUpdate={refreshAbnormalData} />}
            {activeTab === 'envData' && <EnvironmentDataManagement onDataUpdate={refreshAbnormalData} />}
          </>
        )}
      </main>

      {/* 警报弹窗 */}
      {showAlertModal && currentAlert && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2000
        }}>
          <div className="modal" style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '10px',
            width: '500px',
            maxWidth: '90%',
            boxShadow: '0 5px 20px rgba(0,0,0,0.3)',
            border: currentAlert.alert_type === 'device_fault' ? '3px solid #dc3545' : '3px solid #ffc107'
          }}>
            <h3 style={{
              color: currentAlert.alert_type === 'device_fault' ? '#dc3545' : '#ffc107',
              marginBottom: '15px'
            }}>
              {currentAlert.alert_type === 'device_fault' ? '⚠️ 设备故障预警' : '⚠️ 数据异常预警'}
            </h3>

            <div style={{
              backgroundColor: currentAlert.alert_type === 'device_fault' ? '#fff3cd' : '#e7f3ff',
              border: currentAlert.alert_type === 'device_fault' ? '1px solid #ffeaa7' : '1px solid #b3d7ff',
              padding: '15px',
              borderRadius: '6px',
              marginBottom: '20px'
            }}>
              <p style={{margin: '0 0 10px 0', fontWeight: 'bold'}}>
                {currentAlert.message}
              </p>
              {currentAlert.alert_type === 'data_abnormal' && currentAlert.data_id && (
                <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                  数据编号: {currentAlert.data_id}
                </p>
              )}
              {currentAlert.alert_type === 'device_fault' && currentAlert.device_id && (
                <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                  设备ID: {currentAlert.device_id}
                </p>
              )}
              {currentAlert.device_type && (
                <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                  设备类型: {currentAlert.device_type}
                </p>
              )}
              {currentAlert.region && (
                <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                  区域: {currentAlert.region}
                </p>
              )}
              {currentAlert.value && currentAlert.alert_type === 'data_abnormal' && (
                <div>
                  <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                    当前值: <strong>{currentAlert.value} {currentAlert.unit || ''}</strong>
                  </p>
                  <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                    阈值范围: [{currentAlert.threshold_lower || 'N/A'}, {currentAlert.threshold_upper || 'N/A'}] {currentAlert.unit || ''}
                  </p>
                </div>
              )}
              <p style={{margin: '5px 0', fontSize: '0.8rem', color: '#666'}}>
                时间: {new Date(currentAlert.time).toLocaleString()}
              </p>
            </div>

            {currentAlert.alert_type === 'data_abnormal' ? (
              <div style={{display: 'flex', justifyContent: 'center', gap: '10px'}}>
                <button
                  onClick={() => {
                    setShowAlertModal(false);
                    setCurrentAlert(null);
                  }}
                  style={{
                    padding: '10px 24px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  确认
                </button>
              </div>
            ) : (
              <div style={{display: 'flex', justifyContent: 'space-between', gap: '10px'}}>
                <button
                  onClick={() => handleAlertAction('ignore')}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  稍后处理
                </button>
                <button
                  onClick={() => handleAlertAction('clear')}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    flex: 1
                  }}
                >
                  标记已修复
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 调整监测值弹窗 */}
      {showValueAdjustModal && currentAlert && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2001
        }}>
          <div className="modal" style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '10px',
            width: '500px',
            maxWidth: '90%',
            boxShadow: '0 5px 20px rgba(0,0,0,0.3)',
            border: '3px solid #007bff'
          }}>
            <h3 style={{color: '#007bff', marginBottom: '15px'}}>
              📝 调整监测值
            </h3>

            <div style={{
              backgroundColor: '#e7f3ff',
              border: '1px solid #b3d7ff',
              padding: '15px',
              borderRadius: '6px',
              marginBottom: '20px'
            }}>
              <p style={{margin: '0 0 10px 0', fontWeight: 'bold'}}>
                设备: {currentAlert.device_id} ({currentAlert.device_type || '未知类型'})
              </p>
              <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                指标: {currentAlert.indicator_name || currentAlert.indicator_id}
              </p>
              <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                阈值范围: [{adjustThreshold.lower}, {adjustThreshold.upper}] {adjustThreshold.unit}
              </p>
              {adjustData && (
                <p style={{margin: '5px 0', fontSize: '0.9rem'}}>
                  原值: <strong style={{color: '#dc3545'}}>{adjustData.monitor_value} {adjustThreshold.unit}</strong>
                </p>
              )}
            </div>

            <div style={{marginBottom: '20px'}}>
              <label style={{display: 'block', marginBottom: '8px', fontWeight: '500'}}>
                输入新监测值 ({adjustThreshold.unit}):
              </label>
              <input
                type="number"
                step="0.01"
                value={adjustValue}
                onChange={(e) => setAdjustValue(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '16px'
                }}
                placeholder={`请输入 ${adjustThreshold.lower} 到 ${adjustThreshold.upper} 之间的值`}
              />
              <div style={{
                marginTop: '5px',
                fontSize: '0.85rem',
                color: '#666'
              }}>
                有效范围: {adjustThreshold.lower} ~ {adjustThreshold.upper}
              </div>
            </div>

            <div style={{display: 'flex', justifyContent: 'space-between', gap: '10px'}}>
              <button
                onClick={() => {
                  setShowValueAdjustModal(false);
                  setAdjustValue('');
                  setAdjustData(null);
                  setAdjustThreshold({ lower: 0, upper: 0, unit: '' });
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  flex: 1
                }}
                disabled={adjusting}
              >
                取消
              </button>
              <button
                onClick={handleValueAdjust}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  flex: 1
                }}
                disabled={adjusting}
              >
                {adjusting ? '处理中...' : '确认调整'}
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="app-footer">
        <p>© 2024 国家公园智慧林草系统 - 生态环境监测业务线</p>
        <p>系统状态: <span className="status-online">在线</span></p>
        {deviceAlerts.length > 0 && (
          <p style={{color: '#dc3545', fontWeight: 'bold'}}>
            ⚠️ 有 {deviceAlerts.length} 个设备警报
          </p>
        )}
      </footer>
    </div>
  );
}

export default App;
