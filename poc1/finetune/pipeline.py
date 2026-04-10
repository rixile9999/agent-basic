"""
파인튜닝 파이프라인: 데이터 업로드 → job 제출 → 완료 대기 → 결과 저장

사용법:
  # 전체 파이프라인 (데이터 생성 포함)
  uv run python -m poc1.finetune.pipeline

  # 이미 생성된 JSONL 파일로 바로 제출
  uv run python -m poc1.finetune.pipeline --skip-datagen

  # 특정 JSONL 파일 지정
  uv run python -m poc1.finetune.pipeline --file poc1/finetune/train.jsonl
"""
import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import dashscope
from dashscope.customize.finetunes import FineTunes

from poc1.config import DASHSCOPE_BASE_URL
from poc1.finetune.data_gen import OUTPUT_DIR, TRAIN_FILE, run as generate_data

log = logging.getLogger(__name__)

RESULT_FILE = OUTPUT_DIR / "finetune_result.json"

# 파인튜닝 대상 모델 (소형 모델 우선)
FINETUNE_MODEL = "qwen3-1.7b"

# 하이퍼파라미터
HYPER_PARAMS = {
    "n_epochs": 3,
    "learning_rate": 2e-4,
    "batch_size": 4,
}


# ── 파일 업로드 ───────────────────────────────────────────────────────────────

def upload_file(path: Path, api_key: str) -> str:
    """JSONL 파일을 DashScope에 업로드하고 file_id 반환."""
    log.info(f"파일 업로드 중: {path} ({path.stat().st_size / 1024:.1f} KB)")
    with open(path, "rb") as f:
        resp = dashscope.Files.upload(
            file=f,
            api_key=api_key,
            purpose="fine-tune",
        )
    if resp.status_code != 200:
        raise RuntimeError(f"파일 업로드 실패: {resp.status_code} {resp.message}")
    file_id = resp.output["uploaded_files"][0]["file_id"]
    log.info(f"  → file_id: {file_id}")
    return file_id


# ── 파인튜닝 job 제출 ─────────────────────────────────────────────────────────

def submit_finetune(file_id: str, api_key: str) -> str:
    """파인튜닝 job 제출 후 job_id 반환."""
    log.info(f"파인튜닝 job 제출: model={FINETUNE_MODEL}")
    resp = FineTunes.call(
        model=FINETUNE_MODEL,
        training_file_ids=[file_id],
        mode="sft",
        hyper_parameters=HYPER_PARAMS,
        api_key=api_key,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"job 제출 실패: {resp.status_code} {resp.message}")
    job_id = resp.output["job_id"]
    log.info(f"  → job_id: {job_id}")
    return job_id


# ── 완료 대기 ─────────────────────────────────────────────────────────────────

def wait_for_completion(job_id: str, api_key: str, poll_interval: int = 30) -> dict:
    """job 완료까지 폴링. 완료 시 결과 dict 반환."""
    log.info(f"파인튜닝 대기 중... (job_id={job_id}, {poll_interval}초마다 확인)")
    while True:
        resp = FineTunes.get(job_id=job_id, api_key=api_key)
        status = resp.output.get("status", "unknown")
        log.info(f"  상태: {status}")

        if status == "succeeded":
            log.info("파인튜닝 완료!")
            return resp.output
        elif status in ("failed", "cancelled"):
            raise RuntimeError(f"파인튜닝 실패: status={status}, detail={resp.output}")

        time.sleep(poll_interval)


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def run_pipeline(
    api_key: str,
    skip_datagen: bool = False,
    train_file: Path | None = None,
) -> dict:
    # 1. 데이터 생성
    if train_file:
        jsonl_path = train_file
        log.info(f"지정된 JSONL 파일 사용: {jsonl_path}")
    elif skip_datagen and TRAIN_FILE.exists():
        jsonl_path = TRAIN_FILE
        log.info(f"기존 JSONL 파일 사용: {jsonl_path}")
    else:
        log.info("=== [1/4] 학습 데이터 생성 ===")
        jsonl_path = await generate_data(api_key)

    # 학습 데이터 샘플 수 확인
    n_samples = sum(1 for _ in open(jsonl_path))
    log.info(f"학습 샘플 수: {n_samples}개")
    if n_samples < 10:
        raise RuntimeError(f"학습 데이터 부족: {n_samples}개 (최소 10개 필요)")

    # 2. 파일 업로드
    log.info("=== [2/4] 파일 업로드 ===")
    file_id = upload_file(jsonl_path, api_key)

    # 3. 파인튜닝 제출
    log.info("=== [3/4] 파인튜닝 job 제출 ===")
    job_id = submit_finetune(file_id, api_key)

    # 4. 완료 대기
    log.info("=== [4/4] 완료 대기 ===")
    result = wait_for_completion(job_id, api_key)

    # 결과 저장
    output = {
        "job_id": job_id,
        "file_id": file_id,
        "model": FINETUNE_MODEL,
        "finetuned_model": result.get("finetuned_output", ""),
        "n_samples": n_samples,
        "hyper_params": HYPER_PARAMS,
        "status": result.get("status"),
        "result_raw": result,
    }
    RESULT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log.info(f"결과 저장: {RESULT_FILE}")
    log.info(f"파인튜닝 모델명: {output['finetuned_model']}")
    return output


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    p = argparse.ArgumentParser(description="DashScope 파인튜닝 파이프라인")
    p.add_argument("--skip-datagen", action="store_true", help="데이터 생성 건너뛰고 기존 JSONL 사용")
    p.add_argument("--file", default=None, help="학습 JSONL 파일 경로 직접 지정")
    args = p.parse_args()

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY 환경변수 필요")

    result = asyncio.run(run_pipeline(
        api_key=api_key,
        skip_datagen=args.skip_datagen,
        train_file=Path(args.file) if args.file else None,
    ))
    print(f"\n파인튜닝 완료!")
    print(f"모델명: {result['finetuned_model']}")
    print(f"다음 단계: 이 모델명을 poc1/config.py MODELS 리스트에 추가 후 평가 실행")


if __name__ == "__main__":
    main()
