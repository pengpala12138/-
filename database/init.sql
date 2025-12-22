-- 创建数据库
CREATE DATABASE IF NOT EXISTS sjk DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sjk;

-- 游客信息表
CREATE TABLE tourists
(
    tourist_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    id_card VARCHAR(18) UNIQUE NOT NULL,
    phone VARCHAR(20),
    entry_time DATETIME,
    exit_time DATETIME,
    entry_method ENUM('online', 'onsite') DEFAULT 'online',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_id_card (id_card),
    INDEX idx_entry_time (entry_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 预约记录表
CREATE TABLE reservations (
    reservation_id VARCHAR(50) PRIMARY KEY,
    tourist_id VARCHAR(50) NOT NULL,
    reservation_date DATE NOT NULL,
    entry_time_slot VARCHAR(50) NOT NULL,
    group_size INT DEFAULT 1,
    status ENUM('confirmed', 'cancelled', 'completed') DEFAULT 'confirmed',
    ticket_amount DECIMAL(10, 2) DEFAULT 0.00,
    payment_status ENUM('pending', 'paid', 'refunded') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tourist_id) REFERENCES tourists(tourist_id) ON DELETE CASCADE,
    INDEX idx_tourist_id (tourist_id),
    INDEX idx_reservation_date (reservation_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 游客轨迹数据表
CREATE TABLE trajectories (
    trajectory_id INT AUTO_INCREMENT PRIMARY KEY,
    tourist_id VARCHAR(50) NOT NULL,
    location_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    area_id VARCHAR(20) NOT NULL,
    off_route BOOLEAN DEFAULT FALSE,
    warning_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tourist_id) REFERENCES tourists(tourist_id) ON DELETE CASCADE,
    INDEX idx_tourist_id (tourist_id),
    INDEX idx_location_time (location_time),
    INDEX idx_area_id (area_id),
    INDEX idx_off_route (off_route)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 流量控制信息表
CREATE TABLE flow_control (
    area_id VARCHAR(50) PRIMARY KEY,
    daily_capacity INT NOT NULL,
    current_visitors INT DEFAULT 0,
    warning_threshold DECIMAL(5, 2) DEFAULT 0.80,
    status ENUM('normal', 'warning', 'restricted') DEFAULT 'normal',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 系统日志表
CREATE TABLE system_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    log_type ENUM('info', 'warning', 'error', 'security') NOT NULL,
    module VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    user_id VARCHAR(50),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_log_type (log_type),
    INDEX idx_module (module),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 备份记录表
CREATE TABLE backup_logs (
    backup_id INT AUTO_INCREMENT PRIMARY KEY,
    backup_type ENUM('full', 'incremental') NOT NULL,
    backup_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    status ENUM('success', 'failed') NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;