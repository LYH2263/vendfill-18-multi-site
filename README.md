# VendFill 售货机补货

按货道容量、库存与在途量计算缺口，生成不超缺口、非负的补货单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4800 |
| API | http://localhost:9800 |
| 文档 | http://localhost:9800/docs |
| Postgres | localhost:5449 |

健康检查：`GET http://localhost:9800/api/health`

## 多点位规则

系统以「当前点位」为唯一作用域，左侧机位列表可切换：

- 货道、销量、补货单、满仓、汇总五处只服务当前点位；切换后列表与生成只作用于该点，A 的单或满仓不会出现在 B 的视图。
- 显式 `location_id` 指向非当前点位的读写一律 `409` 拒绝（跨点写与本点写互斥，两边行数都不增）。
- 写单只走 `POST /api/refills/run`；`GET /api/refills/latest` 等查询接口绝不代写。生成过程中若当前点位被切换，未提交的半套单自动回滚，不留跨点脏行。
- 补货单可作废（`POST /api/refills/{id}/void`）。删除点位时仍有未作废补货单则拒绝并保留数据；无有效单才可删。当前点位不可删除。

## 使用说明

1. 在「点位」新建点位、切换当前点位或删除无单点位。
2. 在「货道」维护当前点位的货道格子与库存。
3. 在「销量」了解当前点位近期出货。
4. 在「补货单」按缺口生成建议补货量，可查看历史单并作废。
5. 在「满仓」「汇总」查看当前点位已满货道与补货合计。

## 开发与测试

```bash
docker compose exec api pytest -q
```
