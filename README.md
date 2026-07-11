# AIM: Production-Ready Attendance Information Manager

AIM is a robust, full-stack attendance management system built with Flask and MySQL, designed for reliability, security, and ease of deployment. It features a layered architecture, comprehensive security measures, monitoring, and a full CI/CD pipeline.

## Overview

AIM provides a complete solution for managing attendance, student records, and administrative tasks. It is built with a focus on security, scalability, and maintainability, making it suitable for production environments.

## Features

*   **Layered Architecture:** Built with Flask (Python) and MySQL, featuring a clear separation of concerns (routes → services → repositories → models).
*   **Robust Authentication:** Implements Argon2id password hashing (OWASP 2025 recommended), CSRF protection, brute-force lockout, breached-password detection via HaveIBeenPwned, and rate limiting.
*   **Enhanced Security:** Integrates Flask-Talisman (CSP/HSTS) and Flask-CORS for comprehensive security headers.
*   **Comprehensive Features:** Includes attendance tracking, student management, an admin panel, and detailed reports with Chart.js visualizations, FullCalendar integration, responsive light/dark themes, and CSV import/export.
*   **Monitoring & Logging:** Configured with a Prometheus metrics endpoint, structured JSON logging, and health checks.
*   **Extensive Testing:** Boasts 84 tests across 7 files with pytest coverage, ensuring high code quality and reliability.
*   **Dockerized Deployment:** Seamless deployment using Docker Compose (multi-stage build, MySQL healthcheck), Gunicorn, and Nginx.
*   **CI/CD Pipeline:** Full continuous integration and continuous deployment pipeline implemented with GitHub Actions, including Bandit, Safety, Flake8, Pytest, and Docker build verification.
*   **Accessibility:** WCAG 2.1 AA compliant with ARIA live regions, semantic HTML, and keyboard navigation.
*   **Encrypted Backups:** Supports encrypted backup and restore functionality for data integrity.

## Tech Stack

*   **Backend:** Python 3.12, Flask 3.1, Gunicorn, Nginx
*   **Database:** MySQL 8.4, Redis (for caching)
*   **Frontend:** Jinja2, Bootstrap 5.3, Chart.js 4, FullCalendar 6
*   **DevOps:** Docker, Docker Compose, GitHub Actions
*   **Security:** Argon2id, Flask-Talisman, Flask-CORS
*   **Testing:** Pytest
*   **Other:** Weasyprint (for PDF reports), Pinned dependencies, pre-commit hooks, custom exceptions, type hints

## Architecture Summary

AIM follows a classic MVC-like layered architecture, ensuring modularity and maintainability:

1.  **Frontend (Jinja2, Bootstrap, Chart.js, FullCalendar):** Renders dynamic web pages and visualizations, interacting with the backend via HTTP requests.
2.  **Backend (Flask, Python):** Handles business logic, authentication, data processing, and API endpoints. It communicates with the database and other services.
3.  **Database (MySQL):** Stores all application data, including user information, attendance records, and configurations.
4.  **Caching (Redis):** Used for session management and potentially for speeding up frequently accessed data.
5.  **Deployment (Docker, Gunicorn, Nginx):** The application is containerized using Docker, served by Gunicorn, and reverse-proxied by Nginx for efficient and secure deployment.
6.  **CI/CD (GitHub Actions):** Automates testing, building, and deployment processes, ensuring code quality and rapid iteration.

```text
User Browser → Nginx → Gunicorn → Flask App → MySQL
                                       → Redis (caching/sessions)
                                       → Prometheus (metrics)
Developer → GitHub Actions → Docker Image → Docker Compose → Nginx
```

## Getting Started

To set up AIM locally, ensure you have Docker and Docker Compose installed. Clone the repository and follow these steps:

```bash
git clone https://github.com/gaganjainse/AIM.git
cd AIM
docker-compose up --build -d
```

This will build the Docker images and start the application services. You can then access the application in your browser at `http://localhost:80` (or the port configured in your Nginx setup).

## Screenshots

| File | Description |
|------|-------------|
| [`01_login.png`](screenshots/01_login.png) | Login page |
| [`02_dashboard.png`](screenshots/02_dashboard.png) | Dashboard with demo data — attendance distribution, yesterday's stats, monthly trend |
| [`03_attendance.png`](screenshots/03_attendance.png) | Attendance marking page with 30 students loaded |
| [`04_admin_controls.png`](screenshots/04_admin_controls.png) | Admin user management page |
| [`05_reports.png`](screenshots/05_reports.png) | Attendance reports with color-coded thresholds |
| [`06_mobile_view.png`](screenshots/06_mobile_view.png) | Mobile responsive layout (375px width) |
| [`07_dark_mode.png`](screenshots/07_dark_mode.png) | Dark mode dashboard |

See [`screenshots/`](screenshots/) for the full set (7 screenshots covering all major views).

## Limitations / Future Work

*   **No Mobile App:** Currently, AIM is a web-only application. A future enhancement could include a dedicated mobile application.
*   **Advanced Reporting:** While current reporting is robust, more advanced analytics and customizable report generation could be explored.
*   **No Production Claims:** This project is designed to be production-ready in terms of architecture and security, but it is not currently deployed in a live production environment with real users.

## Cross-links

*   **GitHub Profile:** [https://github.com/gaganjainse](https://github.com/gaganjainse)
*   **LinkedIn Profile:** [https://linkedin.com/in/gaganjainse](https://linkedin.com/in/gaganjainse)
*   **Portfolio:** [https://gaganjain.vercel.app](https://gaganjain.vercel.app)

---

*Last updated: June 14, 2026*)
