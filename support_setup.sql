USE lpg_distribution;

CREATE TABLE IF NOT EXISTS support_tickets (
  ticket_id   INT AUTO_INCREMENT PRIMARY KEY,
  ticket_number VARCHAR(20) NOT NULL UNIQUE,
  consumer_id INT NOT NULL,
  booking_id  INT NULL,
  category    VARCHAR(50) NOT NULL,
  subject     VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  priority    VARCHAR(20) NOT NULL,
  status      VARCHAR(20) NOT NULL DEFAULT 'open',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL
);
