# Database Integration Plan for Building Analytics Dashboard

## 1. Database Schema

We'll create the following tables:

### Users Table
```sql
CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(256) NOT NULL,  -- Stores hashed passwords
    name VARCHAR(100),
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Datasets Table
```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    owner VARCHAR(50) REFERENCES users(username),
    description TEXT,
    city VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_system BOOLEAN DEFAULT FALSE
);
```

### Buildings Table
```sql
CREATE TABLE buildings (
    building_id VARCHAR(50) NOT NULL,
    dataset_id INT REFERENCES datasets(id),
    city VARCHAR(50),
    year INT,
    latitude FLOAT,
    longitude FLOAT,
    energy_consumption FLOAT,
    co2_usage FLOAT,
    water_usage FLOAT,
    energy_intensity FLOAT,
    co2_intensity FLOAT,
    true_energy_label VARCHAR(10),
    true_ges_label VARCHAR(10),
    address TEXT,
    street_number VARCHAR(20),
    street_name VARCHAR(100),
    postal_code VARCHAR(20),
    commune_name VARCHAR(100),
    address_id VARCHAR(50),
    construction_year INT,
    surface_area FLOAT,
    log1p_energy_consumption FLOAT,
    log1p_co2_usage FLOAT,
    log1p_energy_intensity FLOAT,
    log1p_co2_intensity FLOAT,
    pc1 FLOAT,
    pc2 FLOAT,
    cluster INT,
    PRIMARY KEY (building_id, dataset_id, year)
);
```

### Security Logs Table
```sql
CREATE TABLE security_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    username VARCHAR(50),
    success BOOLEAN DEFAULT TRUE,
    details JSONB,
    ip_address VARCHAR(50)
);
```

### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50) NOT NULL,
    username VARCHAR(50),
    dataset VARCHAR(100),
    entity_id VARCHAR(50),
    changes JSONB
);
```

## 2. Migration Plan

1. Create PostgreSQL database
2. Set up tables from schema
3. Migrate existing user data
4. Migrate city datasets
5. Migrate ownership information
6. Update application code to use database connections

## 3. Implementation Tasks

1. Install PostgreSQL dependencies
2. Create database connection module
3. Update authentication module
4. Update data loading module
5. Update dataset ownership module
6. Update logging module
7. Update main application logic
