export const API_BASE_URL = 'http://192.168.69.44:5000/api';

export const MENU_ITEMS = [
  { key: 'dashboard', label: '仪表板', icon: 'dashboard' },
  { key: 'tourists', label: '游客管理', icon: 'user' },
  { key: 'reservations', label: '预约管理', icon: 'calendar' },
  { key: 'trajectory', label: '轨迹监控', icon: 'compass' },
  { key: 'flow-control', label: '流量控制', icon: 'bar-chart' },
  { key: 'check-in', label: '入园核验', icon: 'check-circle' },
  { key: 'realtime', label: '实时监控', icon: 'video-camera' },
  { key: 'statistics', label: '数据统计', icon: 'pie-chart' },
  { key: 'logs', label: '系统日志', icon: 'file-text' },
];
export const ECO_FEEDBACK_TYPES = [
  { value: '垃圾处理', label: '垃圾处理' },
  { value: '植被破坏', label: '植被破坏' },
  { value: '动物干扰', label: '动物干扰' },
  { value: '水体污染', label: '水体污染' },
  { value: '其他', label: '其他' },
];

export const ECO_STATUS_COLORS = {
  '待处理': 'orange',
  '处理中': 'blue',
  '已解决': 'green',
  '已忽略': 'default',
};
export const AREA_OPTIONS = [
  { value: 'A001', label: 'A区 - 主入口' },
  { value: 'A002', label: 'B区 - 园林区' },
  { value: 'A003', label: 'C区 - 休闲区' },
  { value: 'A004', label: 'D区 - 观景区' },
];

export const ENTRY_METHOD_OPTIONS = [
  { value: 'online', label: '线上预约' },
  { value: 'onsite', label: '现场购票' },
];

export const RESERVATION_STATUS_OPTIONS = [
  { value: 'confirmed', label: '已确认', color: 'green' },
  { value: 'cancelled', label: '已取消', color: 'red' },
  { value: 'completed', label: '已完成', color: 'blue' },
];

export const PAYMENT_STATUS_OPTIONS = [
  { value: 'pending', label: '待支付' },
  { value: 'paid', label: '已支付' },
  { value: 'refunded', label: '已退款' },
];