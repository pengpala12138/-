import axios from 'axios';

const API_BASE_URL = 'http://172.20.10.7:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      // 处理未授权
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error.response?.data || error.message);
  }
);

// 系统状态
export const getSystemStatus = () => api.get('/status');

// 游客管理
export const getTourists = (params) => api.get('/tourists', { params });
export const createTourist = (data) => api.post('/tourists', data);
export const getTouristById = (id) => api.get(`/tourists/${id}`);
export const updateTourist = (id, data) => api.put(`/tourists/${id}`, data);
export const deleteTourist = (id) => api.delete(`/tourists/${id}`);

// 预约管理
export const getReservations = (params) => api.get('/reservations', { params });
export const createReservation = (data) => api.post('/reservations', data);

// 入园核验
 export const checkInTourist = (data) => api.post('/check-in', data);
// export const checkInTourist = async (data) => {
//   try {
//     console.log('提交入园参数：', JSON.stringify(data)); // 调试：打印参数
//     const response = await api.post('/check-in', data);
//     return response.data;
//   } catch (error) {
//     // 分类型捕获错误，输出真实原因
//     if (error.response) {
//       // 后端返回的错误（4xx/5xx）
//       const { status, data } = error.response;
//       const errorMsg = `后端错误(${status})：${data.message || data.error || '未知错误'}`;
//       console.error('入园核验后端错误：', errorMsg, data);
//       throw new Error(errorMsg);
//     } else if (error.request) {
//       // 网络错误（后端未响应）
//       console.error('入园核验网络错误：', error.request);
//       throw new Error('网络错误：无法连接到后端服务，请检查后端是否启动');
//     } else {
//       // 请求配置错误（参数/格式问题）
//       console.error('入园核验参数错误：', error.message);
//       throw new Error(`请求配置错误：${error.message}`);
//     }
//   }
// };

// 实时监控
export const getRealtimeMonitor = () => api.get('/realtime-monitor');

// 数据视图
export const getDataView = (viewName, params) =>
  api.get(`/views/${viewName}`, { params });

// 存储过程
export const executeProcedure = (procName, data) =>
  api.post(`/procedures/${procName}`, data);

// 统计数据
export const getStatistics = () => api.get('/stats');

// 系统日志
export const getSystemLogs = (params) => api.get('/logs', { params });
export const getFlowControl = () => axiosInstance.get('/flow-control').then(res => res.data);
export const updateFlowControl = (areaId, data) => axiosInstance.put(`/flow-control/${areaId}`, data).then(res => res.data);
// api.js
export const apiRequest = async (method, endpoint, data = null) => {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`http://172.20.10.7:5000${endpoint}`, options);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || '请求失败');
    }

    return result;
  } catch (error) {
    console.error('API请求失败:', error);
    throw error;
  }
};
/**
 * 更新预约信息（如支付状态、预约状态等）
 * @param {string} reservationId - 预约编号
 * @param {Object} data - 需要更新的字段，例如 { payment_status: 'paid' }
 */
export const updateReservation = async (reservationId, data) => {
  try {
    // 注意：这里的 URL 必须与后端 app.py 中定义的路由匹配
    const response = await axios.put(`${API_BASE_URL}/reservations/${reservationId}`, data);
    return response.data;
  } catch (error) {
    console.error('更新预约失败:', error);
    throw error;
  }
};
/**
 * 提交生态保护反馈
 * @param {Object} feedbackData - 包含 tourist_id, area_id, feedback_type, content
 */
export const submitEcologicalFeedback = async (feedbackData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/ecological-feedback`, feedbackData);
    return response.data;
  } catch (error) {
    console.error('提交反馈失败:', error);
    throw error;
  }
};

/**
 * 获取角色化生态统计数据（调用数据库视图）
 * @param {string} role - 'manager' (管理层视图) 或 'officer' (监管员视图)
 */
export const getEcoStatsByRole = async (role) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/eco-stats/${role}`);
    return response.data;
  } catch (error) {
    console.error('获取生态统计失败:', error);
    throw error;
  }
};
export default api;