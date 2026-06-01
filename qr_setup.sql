USE lpg_distribution;

-- Add QR columns to bookings (ignore errors if they already exist)
ALTER TABLE bookings ADD COLUMN qr_token VARCHAR(64) NULL;
ALTER TABLE bookings ADD COLUMN qr_generated_at DATETIME NULL;
ALTER TABLE bookings ADD COLUMN qr_expires_at DATETIME NULL;
ALTER TABLE bookings ADD COLUMN is_qr_used TINYINT(1) DEFAULT 0;
ALTER TABLE bookings ADD COLUMN delivery_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE bookings ADD COLUMN delivered_at DATETIME NULL;

CREATE TABLE IF NOT EXISTS delivery_agents (
  agent_id   INT AUTO_INCREMENT PRIMARY KEY,
  full_name  VARCHAR(100) NOT NULL,
  phone      VARCHAR(15)  NOT NULL,
  agency_id  INT          NOT NULL,
  is_active  TINYINT(1)   DEFAULT 1,
  created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
);

CREATE TABLE IF NOT EXISTS qr_codes (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  booking_id   INT      NOT NULL UNIQUE,
  token        VARCHAR(64) NOT NULL UNIQUE,
  qr_payload   JSON     NOT NULL,
  qr_image_b64 LONGTEXT NULL,
  expires_at   DATETIME NOT NULL,
  is_active    TINYINT(1) DEFAULT 1,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

CREATE TABLE IF NOT EXISTS qr_scan_logs (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  qr_code_id  INT         NOT NULL,
  agent_id    INT         NULL,
  action      VARCHAR(30) NOT NULL,
  scan_result VARCHAR(20) NOT NULL,
  device_info VARCHAR(200) NULL,
  ip_address  VARCHAR(45) NULL,
  scanned_at  DATETIME    DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (qr_code_id) REFERENCES qr_codes(id)
);

SELECT 'QR tables created successfully' AS status;