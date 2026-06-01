CREATE TABLE booking_restrictions (
    consumer_type VARCHAR(20) PRIMARY KEY, -- domestic, essential, commercial
    min_gap_days INT DEFAULT 15,
    max_cylinders_month INT DEFAULT 1
);

-- Insert default rules
INSERT INTO booking_restrictions VALUES ('domestic', 15, 1), ('essential', 7, 5), ('commercial', 0, 10);