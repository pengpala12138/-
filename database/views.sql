-- 1. 客服人员视图：游客基本信息查询（修正）
CREATE OR REPLACE VIEW vw_tourist_info_for_customer_service AS
SELECT
    t.tourist_id,
    t.name,
    t.id_card,
    t.phone,
    t.entry_method,
    r.reservation_date,
    r.entry_time_slot,
    r.status as reservation_status,
    r.payment_status,
    t.entry_time,
    t.exit_time,
    CASE
        WHEN t.entry_time IS NOT NULL AND t.exit_time IS NULL THEN '在园中'
        WHEN t.exit_time IS NOT NULL THEN '已离园'
        ELSE '未入园'
    END as current_status
FROM tourists t
LEFT JOIN reservations r ON t.tourist_id = r.tourist_id  -- 修正：通过tourist_id关联
ORDER BY t.created_at DESC;

-- 2. 安保人员视图：实时游客位置与轨迹（修正）
CREATE OR REPLACE VIEW vw_security_realtime_tracking AS
SELECT
    t.tourist_id,
    t.name,
    t.id_card,
    tr.location_time,
    tr.latitude,
    tr.longitude,
    tr.area_id,
    tr.off_route,
    fc.status as area_status,
    CASE
        WHEN tr.off_route = TRUE THEN '超出规定路线'
        WHEN fc.status = 'warning' THEN '处于预警区域'
        WHEN fc.status = 'restricted' THEN '处于限流区域'
        ELSE '正常'
    END as security_status,
    TIMESTAMPDIFF(MINUTE, tr.location_time, NOW()) as minutes_ago
FROM tourists t
INNER JOIN trajectories tr ON t.tourist_id = tr.tourist_id
LEFT JOIN flow_control fc ON tr.area_id = fc.area_id
WHERE t.entry_time IS NOT NULL
    AND t.exit_time IS NULL
    AND tr.location_time >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
ORDER BY tr.location_time DESC;

-- 3. 管理人员视图：综合统计报表（需要重新设计，因为表结构缺少字段）
CREATE OR REPLACE VIEW vw_management_dashboard AS
SELECT
    DATE(t.entry_time) as visit_date,
    COUNT(DISTINCT t.tourist_id) as total_visitors,
    COUNT(DISTINCT CASE WHEN t.entry_method = 'online' THEN t.tourist_id END) as online_visitors,
    COUNT(DISTINCT CASE WHEN t.entry_method = 'onsite' THEN t.tourist_id END) as onsite_visitors,
    SUM(COALESCE(r.ticket_amount, 0)) as total_revenue,
    AVG(COALESCE(r.group_size, 1)) as avg_group_size,
    COUNT(DISTINCT CASE WHEN tr.off_route = TRUE THEN t.tourist_id END) as off_route_visitors,
    GROUP_CONCAT(DISTINCT fc.area_id ORDER BY fc.current_visitors DESC) as busy_areas
FROM tourists t
LEFT JOIN reservations r ON t.tourist_id = r.tourist_id  -- 修正关联字段
LEFT JOIN trajectories tr ON t.tourist_id = tr.tourist_id
LEFT JOIN flow_control fc ON fc.status IN ('warning', 'restricted')
WHERE t.entry_time IS NOT NULL
    AND DATE(t.entry_time) = CURDATE()
GROUP BY DATE(t.entry_time);

-- 4. 票务人员视图：预约与入园统计（修正）
CREATE OR REPLACE VIEW vw_ticket_sales_analysis AS
SELECT
    r.reservation_date,
    COUNT(*) as total_reservations,
    SUM(CASE WHEN r.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_reservations,
    SUM(CASE WHEN r.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_reservations,
    SUM(CASE WHEN r.status = 'completed' THEN 1 ELSE 0 END) as completed_reservations,
    SUM(r.ticket_amount) as total_sales,
    AVG(r.group_size) as avg_group_size,
    COUNT(DISTINCT CASE WHEN t.entry_time IS NOT NULL THEN t.tourist_id END) as actual_entries,
    CASE
        WHEN COUNT(*) > 0 THEN
            ROUND(COUNT(DISTINCT CASE WHEN t.entry_time IS NOT NULL THEN t.tourist_id END) * 100.0 / COUNT(*), 2)
        ELSE 0
    END as entry_rate_percent
FROM reservations r
LEFT JOIN tourists t ON r.tourist_id = t.tourist_id  -- 修正关联字段
GROUP BY r.reservation_date
ORDER BY r.reservation_date DESC;

-- 5. 监控人员视图：区域流量监控（修正）
CREATE OR REPLACE VIEW vw_area_flow_monitoring AS
SELECT
    fc.area_id,
    fc.daily_capacity,
    fc.current_visitors,
    fc.warning_threshold,
    ROUND(fc.current_visitors * 100.0 / fc.daily_capacity, 2) as capacity_percentage,
    fc.status,
    COUNT(DISTINCT tr.tourist_id) as unique_visitors_last_hour,
    COUNT(CASE WHEN tr.off_route = TRUE THEN 1 END) as off_route_count,
    MAX(tr.location_time) as last_update_time,
    fc.last_updated as flow_control_updated
FROM flow_control fc
LEFT JOIN trajectories tr ON fc.area_id = tr.area_id
    AND tr.location_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY fc.area_id, fc.daily_capacity, fc.current_visitors, fc.warning_threshold, fc.status, fc.last_updated;

-- 6. 数据分析视图：游客行为分析（修正）
CREATE OR REPLACE VIEW vw_tourist_behavior_analysis AS
SELECT
    t.tourist_id,
    t.name,
    t.entry_method,
    COUNT(DISTINCT tr.area_id) as areas_visited,
    MIN(tr.location_time) as first_location_time,
    MAX(tr.location_time) as last_location_time,
    TIMESTAMPDIFF(MINUTE, MIN(tr.location_time), MAX(tr.location_time)) as total_duration_minutes,
    COUNT(CASE WHEN tr.off_route = TRUE THEN 1 END) as off_route_count,
    GROUP_CONCAT(DISTINCT tr.area_id ORDER BY tr.location_time) as visit_sequence,
    COALESCE(r.group_size, 1) as group_size,
    COALESCE(r.ticket_amount, 0) as ticket_amount,
    t.entry_time,
    t.exit_time
FROM tourists t
LEFT JOIN trajectories tr ON t.tourist_id = tr.tourist_id
LEFT JOIN reservations r ON t.tourist_id = r.tourist_id  -- 修正关联字段
WHERE t.entry_time IS NOT NULL
GROUP BY t.tourist_id, t.name, t.entry_method, r.group_size, r.ticket_amount, t.entry_time, t.exit_time;