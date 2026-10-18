# 已保存App显式追加CSV材料：本轮原始证据

{
  "status": "PASS_AUTHOR_FINITE_APP_MATERIAL_BUSINESS_AUTHORIZATION",
  "base": "09695358d03f5c5d6fff2c8bd68bc33048098125",
  "branch": "dev/production-trial-stages-20261018",
  "timestamp": "2026-10-18T23:03:58.814158+00:00",
  "scope": "One existing Goal CSV App, one existing B not granted to App before measurement; explicit App-only READ+SUM24h; original material CHECK/version/same-instance adoption/newB350; cold immutable history; metadata atomic withdrawal after source loss plus late former ACTIVE callback",
  "api": {
    "nodes": 4,
    "outer_seconds": 11.58774688399717,
    "command": "api-qualified-final/command.json",
    "trace_type": "ASGI/TestClient structured actual requests, not wire HTTP",
    "raw_traces": 4
  },
  "installed": {
    "pages": {
      "new-page": {
        "checks": 29,
        "http_requests": 102,
        "phase": "complete",
        "seconds": 133.27495291500236
      },
      "cold-page": {
        "checks": 9,
        "http_requests": 56,
        "phase": "complete",
        "seconds": 41.903051300003426
      },
      "withdraw-page": {
        "checks": 13,
        "http_requests": 61,
        "phase": "complete",
        "seconds": 29.996130266001273
      }
    },
    "wheel": {
      "bytes": 952178,
      "sha256": "0f581efd1c296ae43357cefdf99bb84afaa8cb867004f2ff4d43a9053b9f1e60"
    },
    "package_files": 140,
    "runtime_files_with_tests": 142,
    "runtime_source_unchanged": true,
    "fixture_App_B_grants": 0,
    "app_id": "app_aa95cff6d9b746f994642f7f170635ba",
    "instance_id": "iinstance_9edf4b01b49fa9887575fa01f6715607",
    "core_run_ids": [
      "run_75b47a6562a742789f30f1ec7fb81cf5",
      "run_7e70ee0e781a421c8a47a51edbb304ed",
      "run_ec8db11f0f4b415db45cd8f758ab1f6f"
    ],
    "old_result": "A30/v1",
    "new_result": "B350/v2",
    "goal_version": 1,
    "original_release": "irelease_703d7d71266240fe94fd44e180cdf26d",
    "new_release": "irelease_14596aa68a6f479a94a6bcf1d712fee0",
    "three_ordinary_worker_jobs": "SUCCEEDED fence1",
    "model_attempts": 0,
    "reservations": 0,
    "real_models": 0,
    "human": "PENDING",
    "semantics": "UNKNOWN"
  },
  "negative_proofs": [
    "wrong hash and Strict runtime injection deny without writes",
    "foreign project and missing upstream SUM deny without writes",
    "expiry during App proof rolls back all55 tables",
    "accepted-key body conflict never receives ABSENT proof",
    "stale unrelated permission baseline rejects with exact NOT_ACCEPTED proof, all54 nonheartbeat tables unchanged; fresh explicit scope/consent then success",
    "wrong pure GET key does not become unknown write",
    "source403 clears private results columns Goal revision content; metadata withdrawal remains available",
    "exact B pair rev2 withdrawn atomically; late former ACTIVE GET cannot reinstall view access or Grant; original auth key REVOKED; private B result403"
  ],
  "prior_window": {
    "path": "qualified-installed",
    "status": "PASS_EXACT_SOURCE_SUPERSEDED",
    "note": "Original three-page window PASS before explicit rejection-proof fix; both original source before/after and exact package retained, not relabeled final"
  },
  "boundaries": {
    "Windows": "NOT_RUN",
    "native_browser": "NOT_RUN",
    "PostgreSQL": "NOT_RUN",
    "real_models": "NOT_RUN_CALLS0",
    "real_semantics_and_scenes": "NOT_RUN",
    "real_human_acceptance": "NOT_RUN",
    "full_capacity": "NOT_RUN; AUTH64 requests / control64 material IDs inclA do not qualify64 addedB; existing per-GID metadata withdrawal retained",
    "remote_CI": "NOT_RUN",
    "deploy": "NOT_RUN",
    "real_account_material": "SOURCE_MISSING",
    "old_full_disk_final_review": "NOT_RECOVERED",
    "current_remote_HEAD": "UNKNOWN_ACCESS_NOT_RETRIED",
    "remote_network_auth_operations": 0,
    "pushes": 0
  }
}

产品说明：[业务范围及使用流程](../../csv-app-material-access.md)。原始最终页面：[授权、拒绝退出与材料链](raw/qualified-final/new-page-proof.json)、[冷启动历史](raw/qualified-final/cold-page-proof.json)、[失权清理及撤回迟到隔离](raw/qualified-final/withdraw-page-proof.json)。[安装进程及命令](raw/qualified-final/installed-result.json)、[API命令](raw/api-qualified-final/command.json)、[源散列](raw/final-source-hashes.json)、[修正时序](raw/observer-corrections.md)。

两个安装窗口与全部API迭代、SQLite、轮子、原始stdout/stderr、HTTP结构与实际响应散列、完整表快照、执行脚本及符号链接均在author-originals.tar.gz中；解压后依sealed-manifest逐文件核验。独审另有review-originals.tar.gz与独立manifest，不把静审或观察器推断称为产品执行。安装资格依赖显式既有锁定依赖目录，不声称全新机器依赖下载已验。UI验证为JSDOM执行原产品事件和真实loopback HTTP，无原生浏览器/视觉资格。
