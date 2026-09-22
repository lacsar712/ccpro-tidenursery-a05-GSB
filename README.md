# TideNursery-01 · 潮汐育苗台账

海水育苗场「塘口水质采样与投喂事件」台账种子项目（非库存 / 电商 / 医院）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · python-jose · passlib(bcrypt) · uvicorn |
| 前端 | React 18 · Vite · TypeScript · React Router v6 |
| 数据库 | PostgreSQL 15 |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3400** |
| 后端 API | **8400** |
| PostgreSQL | **5434** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 场长 |
| `technician` | `123456` | 水质技术员 |

## 一键启动

```bash
cd TideNursery-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3400
- 后端健康检查：http://localhost:8400/api/health
- API 文档：http://localhost:8400/docs

后端 entrypoint 流程：等待数据库就绪 → `create_all` 建表 → seed 初始数据 → 启动 uvicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 Password），`/api/auth/login`、`/api/auth/me`
2. **Hatchery 育苗场**：`name`、`seawaterSource`、`notes`
3. **Pond 育苗塘**：`hatcheryId`、`pondCode`、`species`、`volumeM3`、`status(stocked|dry|quarantine)`；同场 `pondCode` 唯一
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **DoCalibration 溶氧探头校准票**：`pondId`、`calibratedAt`、`standardReading`（标准液读数）、`deviceReading`（实机读数）、`validHours`（有效小时数，正整数）、`calibrator`（校准人）
   - 实机读数与标准液读数绝对差 **> 0.5** 时建票失败，返回 **400**
   - 有效性口径（删除或作废以外，唯一以时间窗函数判定）：取塘口**最近一张**校准票，当前时刻落在 `[校准时刻, 校准时刻 + 有效小时数]` 之内即为有效；无票 / 校准时刻在未来 / 超窗均视为失效
   - 新建水质样前强制校验：无有效校准返回 **409**，中文提示带最近票编号（如“最近校准票 #12 已过有效期”）或写明“无溶氧探头校准票”；校准过期后自动恢复拦截，无需改标记
7. **Dashboard**：塘总数、quarantine 数、**溶氧校准失效塘数**、近 24h 采样数、近 7 日投喂总量 kg；失效塘数与塘口列表“校准失效”行数同源一致

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedEvents · DoCalibrations（侧栏「溶氧校准」）

- 塘口列表每行带「溶氧校准」有效/失效标记
- 水质样页选择塘口后显示该校准状态；拦截由服务端强制执行，前端标记仅为提示（绕过前端直接调用 API 同样返回 409）

## 种子数据

初始 4 个塘口中 **B-01 无任何溶氧校准票**（即唯一无有效校准的塘口，对其新建水质样返回 409）；A-02 除一张在有效期内的票外另附一张已过期历史票，用于演示“仅以最近一张票的时间窗为准”。

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8400

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
TideNursery-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
