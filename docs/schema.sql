-- E-Survey MySQL schema reference. Generated from SQLAlchemy models.
-- Use flask --app app init-db for initial setup.


CREATE TABLE rate_limits (
	`key` VARCHAR(64) NOT NULL, 
	count INTEGER NOT NULL, 
	expires_at DATETIME NOT NULL, 
	PRIMARY KEY (`key`)
)

;

CREATE INDEX ix_rate_limits_expires_at ON rate_limits (expires_at);


CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;


CREATE TABLE businesses (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	owner_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	industry VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
)

;

CREATE INDEX ix_businesses_owner_id ON businesses (owner_id);


CREATE TABLE actions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	business_id INTEGER NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id)
)

;

CREATE INDEX ix_actions_business_id ON actions (business_id);


CREATE TABLE surveys (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	business_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	slug VARCHAR(60) NOT NULL, 
	description TEXT NOT NULL, 
	categories JSON NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_id) REFERENCES businesses (id), 
	UNIQUE (slug)
)

;

CREATE INDEX ix_surveys_business_id ON surveys (business_id);


CREATE TABLE reviews (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	business_id INTEGER NOT NULL, 
	survey_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	comment TEXT NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	submission_key VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (survey_id, submission_key), 
	FOREIGN KEY(business_id) REFERENCES businesses (id), 
	FOREIGN KEY(survey_id) REFERENCES surveys (id)
)

;

CREATE INDEX ix_review_business_date ON reviews (business_id, created_at);

CREATE INDEX ix_reviews_survey_id ON reviews (survey_id);