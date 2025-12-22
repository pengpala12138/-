-- 存储过程1：自动更新区域流量状态（修正）
DELIMITER $$

CREATE PROCEDURE sp_update_flow_status()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_area_id VARCHAR(50);
    DECLARE v_daily_capacity INT;
    DECLARE v_current_visitors INT;
    DECLARE v_warning_threshold DECIMAL(5,2);
    DECLARE v_new_status ENUM('normal', 'warning', 'restricted');

    -- 游标遍历所有区域
    DECLARE cur CURSOR FOR
        SELECT area_id, daily_capacity, current_visitors, warning_threshold
        FROM flow_control;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO v_area_id, v_daily_capacity, v_current_visitors, v_warning_threshold;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 根据人数计算状态
        IF v_current_visitors >= v_daily_capacity THEN
            SET v_new_status = 'restricted';
        ELSEIF v_current_visitors >= v_daily_capacity * v_warning_threshold THEN
            SET v_new_status = 'warning';
        ELSE
            SET v_new_status = 'normal';
        END IF;

        -- 更新状态
        UPDATE flow_control
        SET status = v_new_status,
            last_updated = NOW()
        WHERE area_id = v_area_id;

        -- 如果状态变化，记录日志
        IF v_new_status IN ('warning', 'restricted') THEN
            INSERT INTO system_logs (log_type, module, message, created_at)
            VALUES ('warning', 'flow_control',
                    CONCAT('区域 ', v_area_id, ' 进入',
                           CASE v_new_status
                               WHEN 'warning' THEN '预警'
                               ELSE '限流'
                           END, '状态。当前人数: ', v_current_visitors,
                           ', 容量: ', v_daily_capacity),
                    NOW());
        END IF;
    END LOOP;

    CLOSE cur;

    SELECT '区域流量状态更新完成' as result;
END$$

DELIMITER ;

-- 存储过程2：生成每日统计报告（修正）
DELIMITER $$

CREATE PROCEDURE sp_generate_daily_report(IN report_date DATE)
BEGIN
    DECLARE v_total_visitors INT DEFAULT 0;
    DECLARE v_online_reservations INT DEFAULT 0;
    DECLARE v_onsite_tickets INT DEFAULT 0;
    DECLARE v_total_revenue DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_avg_stay_minutes INT DEFAULT 0;
    DECLARE v_off_route_incidents INT DEFAULT 0;
    DECLARE v_warning_areas INT DEFAULT 0;
    DECLARE v_peak_hour VARCHAR(5);
    DECLARE v_visitor_count INT DEFAULT 0;

    -- 计算总游客数
    SELECT COUNT(DISTINCT tourist_id) INTO v_total_visitors
    FROM tourists
    WHERE DATE(entry_time) = report_date AND entry_time IS NOT NULL;

    -- 计算在线预约数（通过reservations表）
    SELECT COUNT(DISTINCT r.tourist_id) INTO v_online_reservations
    FROM reservations r
    INNER JOIN tourists t ON r.tourist_id = t.tourist_id
    WHERE DATE(t.entry_time) = report_date
        AND t.entry_time IS NOT NULL
        AND t.entry_method = 'online';

    -- 计算现场购票数
    SELECT COUNT(DISTINCT tourist_id) INTO v_onsite_tickets
    FROM tourists
    WHERE DATE(entry_time) = report_date
        AND entry_time IS NOT NULL
        AND entry_method = 'onsite';

    -- 计算总收入
    SELECT COALESCE(SUM(r.ticket_amount), 0) INTO v_total_revenue
    FROM reservations r
    INNER JOIN tourists t ON r.tourist_id = t.tourist_id
    WHERE DATE(t.entry_time) = report_date
        AND t.entry_time IS NOT NULL
        AND r.payment_status = 'paid';

    -- 计算平均停留时间
    SELECT COALESCE(AVG(TIMESTAMPDIFF(MINUTE, entry_time, COALESCE(exit_time, NOW()))), 0)
    INTO v_avg_stay_minutes
    FROM tourists
    WHERE DATE(entry_time) = report_date
        AND entry_time IS NOT NULL;

    -- 计算偏离路线事件数
    SELECT COUNT(DISTINCT tourist_id) INTO v_off_route_incidents
    FROM trajectories
    WHERE off_route = TRUE
        AND DATE(location_time) = report_date;

    -- 计算预警区域数
    SELECT COUNT(DISTINCT area_id) INTO v_warning_areas
    FROM flow_control
    WHERE status IN ('warning', 'restricted');

    -- 计算高峰时段
    SELECT HOUR(location_time) INTO v_peak_hour
    FROM trajectories
    WHERE DATE(location_time) = report_date
    GROUP BY HOUR(location_time)
    ORDER BY COUNT(*) DESC
    LIMIT 1;

    -- 返回结果
    SELECT
        report_date as stat_date,
        v_total_visitors as total_visitors,
        v_online_reservations as online_reservations,
        v_onsite_tickets as onsite_tickets,
        v_total_revenue as total_revenue,
        v_avg_stay_minutes as avg_stay_minutes,
        v_off_route_incidents as off_route_incidents,
        v_warning_areas as warning_areas,
        CONCAT(v_peak_hour, ':00') as peak_hour;

END$$

DELIMITER ;

-- 存储过程3：批量处理过期预约（修正）
DELIMITER $$

CREATE PROCEDURE sp_process_expired_reservations()
BEGIN
    DECLARE rows_affected INT DEFAULT 0;
    DECLARE start_time DATETIME DEFAULT NOW();

    -- 标记过期预约（预约日期已过且游客未入园）
    UPDATE reservations r
    SET r.status = 'cancelled',
        r.updated_at = NOW()
    WHERE r.status = 'confirmed'
        AND r.reservation_date < CURDATE()
        AND NOT EXISTS (
            SELECT 1
            FROM tourists t
            WHERE t.tourist_id = r.tourist_id
                AND t.entry_time IS NOT NULL
        );

    SET rows_affected = ROW_COUNT();

    -- 记录操作日志
    INSERT INTO system_logs (log_type, module, message, created_at)
    VALUES ('info', 'reservation',
            CONCAT('批量处理过期预约完成，处理数量: ', rows_affected),
            NOW());

    SELECT rows_affected as processed_count;
END$$

DELIMITER ;

-- 存储过程4：清理过期轨迹数据（新增）
DELIMITER $$

CREATE PROCEDURE sp_cleanup_old_trajectories(IN days_to_keep INT)
BEGIN
    DECLARE deleted_rows INT DEFAULT 0;
    DECLARE backup_count INT DEFAULT 0;

    -- 首先备份要删除的数据
    CREATE TEMPORARY TABLE IF NOT EXISTS temp_old_trajectories AS
    SELECT * FROM trajectories
    WHERE location_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);

    SELECT COUNT(*) INTO backup_count FROM temp_old_trajectories;

    -- 删除旧数据
    DELETE FROM trajectories
    WHERE location_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);

    SET deleted_rows = ROW_COUNT();

    -- 记录备份日志
    INSERT INTO backup_logs (backup_type, backup_path, file_size, status, start_time, end_time, message)
    VALUES ('incremental', 'temp_old_trajectories', backup_count, 'success', start_time, NOW(),
            CONCAT('清理了 ', deleted_rows, ' 条轨迹数据，备份到临时表'));

    -- 记录系统日志
    INSERT INTO system_logs (log_type, module, message, created_at)
    VALUES ('info', 'maintenance',
            CONCAT('清理过期轨迹数据完成，删除了 ', deleted_rows, ' 条记录'),
            NOW());

    SELECT deleted_rows as deleted_count, backup_count as backup_count;
END$$

DELIMITER ;

-- 触发器1：自动记录游客入园时间（修正）
DELIMITER $$

CREATE TRIGGER trg_after_tourist_entry_update
AFTER UPDATE ON tourists
FOR EACH ROW
BEGIN
    -- 当入园时间被设置时，更新相关数据
    IF NEW.entry_time IS NOT NULL AND OLD.entry_time IS NULL THEN
        -- 更新预约状态为已完成
        UPDATE reservations
        SET status = 'completed',
            updated_at = NOW()
        WHERE tourist_id = NEW.tourist_id
            AND reservation_date = DATE(NEW.entry_time)
            AND status = 'confirmed';

        -- 记录入园日志
        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
        VALUES ('info', 'entry',
                CONCAT('游客 ', NEW.name, ' (ID: ', NEW.tourist_id, ') 已入园'),
                NEW.tourist_id,
                NOW());
    END IF;

    -- 当离园时间被设置时
    IF NEW.exit_time IS NOT NULL AND OLD.exit_time IS NULL THEN
        -- 获取游客最后所在的区域
        UPDATE flow_control fc
        SET fc.current_visitors = GREATEST(fc.current_visitors - 1, 0),
            fc.last_updated = NOW()
        WHERE fc.area_id = (
            SELECT area_id
            FROM trajectories
            WHERE tourist_id = NEW.tourist_id
            ORDER BY location_time DESC
            LIMIT 1
        );

        -- 记录离园日志
        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
        VALUES ('info', 'exit',
                CONCAT('游客 ', NEW.name, ' (ID: ', NEW.tourist_id, ') 已离园'),
                NEW.tourist_id,
                NOW());
    END IF;
END$$

DELIMITER ;

-- 触发器2：检测超出规定路线并预警（修正）
DELIMITER $$

CREATE TRIGGER trg_after_trajectory_insert
AFTER INSERT ON trajectories
FOR EACH ROW
BEGIN
    DECLARE v_tourist_name VARCHAR(100);
    DECLARE v_area_id_exists INT;

    -- 检查区域是否存在
    SELECT COUNT(*) INTO v_area_id_exists
    FROM flow_control
    WHERE area_id = NEW.area_id;

    -- 如果区域不存在，则插入到flow_control表（默认容量）
    IF v_area_id_exists = 0 THEN
        INSERT INTO flow_control (area_id, daily_capacity, current_visitors, status)
        VALUES (NEW.area_id, 100, 0, 'normal');
    END IF;

    -- 当检测到超出规定路线时
    IF NEW.off_route = TRUE AND NEW.warning_sent = FALSE THEN
        -- 获取游客姓名
        SELECT name INTO v_tourist_name
        FROM tourists
        WHERE tourist_id = NEW.tourist_id;

        -- 记录安全预警日志
        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
        VALUES ('warning', 'security',
                CONCAT('安全预警：游客 ', v_tourist_name,
                       ' (ID: ', NEW.tourist_id, ') 在区域 ',
                       NEW.area_id,
                       ' 超出规定路线。坐标: (',
                       NEW.latitude, ', ', NEW.longitude, ')'),
                NEW.tourist_id,
                NOW());

        -- 标记警告已发送
        UPDATE trajectories
        SET warning_sent = TRUE
        WHERE trajectory_id = NEW.trajectory_id;
    END IF;
END$$

DELIMITER ;

-- 触发器3：自动更新区域人数（新增）
DELIMITER $$

CREATE TRIGGER trg_after_trajectory_insert_flow_update
AFTER INSERT ON trajectories
FOR EACH ROW
BEGIN
    DECLARE v_visitor_in_area INT DEFAULT 0;

    -- 统计该区域内过去30分钟内有多少不同的游客
    SELECT COUNT(DISTINCT tourist_id) INTO v_visitor_in_area
    FROM trajectories
    WHERE area_id = NEW.area_id
        AND location_time >= DATE_SUB(NOW(), INTERVAL 30 MINUTE);

    -- 更新flow_control表中的当前人数
    UPDATE flow_control
    SET current_visitors = v_visitor_in_area,
        last_updated = NOW()
    WHERE area_id = NEW.area_id;

END$$

DELIMITER ;

-- 触发器4：自动更新预约记录关联（修正）
DELIMITER $$

CREATE TRIGGER trg_before_reservation_insert
BEFORE INSERT ON reservations
FOR EACH ROW
BEGIN
    DECLARE v_tourist_exists INT;

    -- 检查游客是否存在
    SELECT COUNT(*) INTO v_tourist_exists
    FROM tourists
    WHERE tourist_id = NEW.tourist_id;

    IF v_tourist_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '游客ID不存在，请先创建游客信息';
    END IF;
END$$

DELIMITER ;

-- 触发器5：自动记录数据变更（新增）
DELIMITER $$

CREATE TRIGGER trg_after_tourist_update_log
AFTER UPDATE ON tourists
FOR EACH ROW
BEGIN
    -- 如果姓名、身份证或手机号发生变化，记录日志
    IF NEW.name <> OLD.name OR NEW.id_card <> OLD.id_card OR NEW.phone <> OLD.phone THEN
        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
        VALUES ('info', 'tourist_update',
                CONCAT('游客信息更新：', OLD.name, ' -> ', NEW.name,
                       ' (ID: ', NEW.tourist_id, ')'),
                NEW.tourist_id,
                NOW());
    END IF;
END$$

DELIMITER ;