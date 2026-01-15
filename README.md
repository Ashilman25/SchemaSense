# SchemaSense

> **Intelligent Database Design & Querying Platform**
> Natural language to SQL conversion, interactive schema visualization, and real-time database management.

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://schema-sense.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?logo=postgresql)](https://www.postgresql.org/)
[![Deployed](https://img.shields.io/badge/deployment-vercel%20%2B%20render-black)](https://schema-sense.com)

---

## 🎯 Overview

**SchemaSense** is a full-stack database design and query platform that combines natural language processing, interactive visual editing, and real time PostgreSQL management. Users can design database schemas visually, generate SQL from plain English questions, and interact with managed databases - all without leaving the browser.

**🌐 Live Demo:** [https://schema-sense.com](https://schema-sense.com)

---

## ✨ Key Features

### 🤖 Natural Language to SQL
- **AI-Powered Query Generation**: Convert plain English questions into optimized SQL queries using OpenAI GPT-4
- **Context-Aware**: Automatically analyzes your database schema to generate accurate, schema-specific queries
- **Query Validation**: Real-time syntax checking and safety validation before execution

### 📊 Interactive ER Diagram Editor
- **Visual Schema Design**: Drag-and-drop interface for creating tables, columns, and relationships
- **Live DDL Generation**: Automatically generates PostgreSQL DDL as you design
- **Bi-Directional Editing**: Edit via visual diagram OR raw DDL—changes sync in real-time
- **Relationship Management**: Visual foreign key creation with automatic constraint generation

### 🗄️ Managed Database Provisioning
- **One-Click Databases**: Provision isolated PostgreSQL databases instantly (powered by Neon)
- **Session Isolation**: Each user gets their own isolated database environment with secure credential management
- **Sample Data**: Optional pre-populated sales database for testing and demos
- **Automatic Cleanup**: TTL-based lifecycle management to reclaim unused resources

### 📈 Query Execution & Analysis
- **Visual Query Results**: Interactive table views with sortable columns
- **Execution Plans**: EXPLAIN ANALYZE visualization for query optimization
- **Query History**: Persistent history with search and replay functionality
- **Performance Metrics**: Execution time tracking and performance insights

### 🎨 Modern User Experience
- **Dark/Light Mode**: System-aware theme with manual toggle
- **Responsive Design**: Works seamlessly on desktop and tablet
- **Real-Time Updates**: Live schema synchronization across all panels
- **Undo/Redo**: Full history stack for schema modifications

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ Query Builder│  │ ER Diagram   │  │ Schema Explorer    │     │
│  │   Panel      │  │   Editor     │  │     Panel          │     │
│  └──────────────┘  └──────────────┘  └────────────────────┘     │
│           ▲                 ▲                  ▲                │
└───────────┼─────────────────┼──────────────────┼────────────────┘
            │                 │                  │
            │  HTTPS + CORS + Session Cookies    │
            │                 │                  │
┌───────────▼─────────────────▼──────────────────▼─────────────────┐
│                    Backend API (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │  NL-to-SQL   │  │ Schema Mgmt  │  │  DB Provisioning   │      │
│  │  (OpenAI)    │  │   Engine     │  │      Engine        │      │
│  └──────────────┘  └──────────────┘  └────────────────────┘      │
│           │                 │                  │                 │
│           └─────────────────┴──────────────────┘                 │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                ┌─────────────▼───────────────┐
                │   PostgreSQL Cluster        │
                │   (Neon Serverless)         │
                │                             │
                │  • Admin Database           │
                │  • User Database Pool       │
                │  • Session Tracking         │
                └─────────────────────────────┘
```

### Technology Stack

**Frontend**
- **Framework**: React 18 with Vite
- **Routing**: React Router v6
- **State Management**: React Context + Hooks
- **Visualization**: ReactFlow for ER diagrams
- **Styling**: TailwindCSS + shadcn/ui components
- **Deployment**: Vercel (CDN + Edge Network)

**Backend**
- **Framework**: FastAPI (Python 3.11+)
- **Database Driver**: psycopg2 (PostgreSQL adapter)
- **AI Integration**: OpenAI GPT-4 API
- **Session Management**: Signed cookies with itsdangerous
- **Security**: CORS, rate limiting, SQL injection prevention
- **Deployment**: Render (managed containers)

**Database**
- **Platform**: Neon Serverless PostgreSQL
- **Features**: Auto-scaling, branching, connection pooling
- **Security**: SSL/TLS, isolated credentials per session

**Infrastructure**
- **Domain**: Custom domain with subdomain architecture
- **SSL**: Automatic TLS certificates (Vercel + Render)
- **Session**: Cookie-based with cross-subdomain support
- **Monitoring**: Render metrics + custom logging

---

## 🔐 Security & Architecture Highlights

### Session Isolation
Each user session gets:
- **Unique session ID**: Cryptographically signed cookies
- **Isolated database credentials**: Dedicated PostgreSQL role per session
- **No cross-contamination**: Sessions cannot access each other's data

### Production-Grade Security
- **HTTPS Everywhere**: TLS 1.3 on all connections
- **CORS Protection**: Strict origin validation
- **Rate Limiting**: 50 requests/hour for database provisioning
- **SQL Injection Prevention**: Parameterized queries only
- **Secure Cookies**: `HttpOnly`, `Secure`, `SameSite=Lax`
- **Safari ITP Compatible**: Custom domain architecture for cross-browser support

### Resource Management
- **TTL Cleanup**: Automatic deletion of databases after 14 days of inactivity
- **Connection Pooling**: Efficient database connection management
- **Query Timeouts**: 15-second statement timeout to prevent runaway queries
- **Quota Limits**: 5 databases per session, 100 global maximum

---

## 🚀 Quick Start

### Option 1: Use the Live Demo
Visit **[https://schema-sense.com](https://schema-sense.com)** and click **"Provision Database with Sample Data"** to get started instantly.

### Option 2: Use Personal Database
Visit **[https://schema-sense.com](https://schema-sense.com)** and connect your own personal PostgreSQL database and begin editing instantly.

---

## 📋 Usage Examples

### Natural Language Queries

```plaintext
User Input:
  "Show me the top 5 customers by total revenue"

Generated SQL:
  SELECT
    c.customer_id,
    c.name,
    SUM(o.total_amount) as total_revenue
  FROM customers c
  JOIN orders o ON c.customer_id = o.customer_id
  GROUP BY c.customer_id, c.name
  ORDER BY total_revenue DESC
  LIMIT 5;
```

### Visual Schema Design

1. **Add Table**: Click "Add Table" → Enter table name
2. **Add Columns**: Define column names, types, and constraints
3. **Create Relationships**: Drag from foreign key column to primary key
4. **Generate DDL**: Switch to DDL view to see generated SQL
5. **Apply to Database**: Click "Apply Changes" to execute DDL

### DDL Editing

```sql
-- Edit raw SQL in the DDL editor
CREATE TABLE products (
  product_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  category_id INTEGER REFERENCES categories(category_id)
);

-- Changes automatically reflected in ER diagram
```

---

## 🏆 Technical Achievements

### Cross-Browser Cookie Compatibility
- Implemented custom domain architecture (`schema-sense.com` + `api.schema-sense.com`) to solve Safari's Intelligent Tracking Prevention (ITP)
- Proper `SameSite` cookie configuration for same-site subdomain sharing
- Session persistence across all major browsers (Chrome, Safari, Firefox, Edge)

### Real-Time Schema Synchronization
- Bi-directional editing between visual diagram and raw DDL
- Conflict-free merging of concurrent schema changes
- Undo/redo stack with 10-level history

### Scalable Database Provisioning
- Dynamic database creation with unique credentials per session
- Automatic PostgreSQL role creation with secure password generation
- Connection pooling and lifecycle management

### AI Integration
- GPT-4 integration with schema-aware prompt engineering
- Context injection for accurate query generation
- Fallback handling and error recovery



## 🚀 Deployment

**Production Setup:**
- **Frontend**: Vercel (automatic deployments from `main` branch)
- **Backend**: Render (automatic deployments from `main` branch)
- **Database**: Neon Serverless PostgreSQL (auto-scaling)



## 📊 Performance

- **Query Execution**: < 100ms for most queries (excluding complex aggregations)
- **Schema Rendering**: < 200ms for diagrams with 50+ tables
- **Database Provisioning**: ~3-5 seconds (includes role creation + sample data)
- **API Response Time**: P95 < 300ms
- **Frontend Load Time**: < 2 seconds (cached assets)



## 🙏 Acknowledgments

- **OpenAI GPT-4** for natural language processing
- **Neon** for serverless PostgreSQL infrastructure
- **Vercel** for frontend hosting and edge network
- **Render** for backend container orchestration
- **ReactFlow** for ER diagram visualization



## 🔮 Future Enhancements

- [ ] Multi-database support (MySQL, SQLite, MongoDB)
- [ ] Collaborative editing (real-time multiplayer)
- [ ] Export to ORM models (SQLAlchemy, Prisma, TypeORM)
- [ ] Query optimization suggestions
- [ ] Database migration history
- [ ] Role-based access control (RBAC)
- [ ] Jupyter notebook integration

---

<div align="center">

**Built with ❤️ using React, FastAPI, and PostgreSQL**

[Live Demo](https://schema-sense.com) 

</div>
