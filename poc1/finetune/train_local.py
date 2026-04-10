"""
로컬 GPU (RTX 4090) LoRA 파인튜닝
Unsloth 기반 Qwen3-1.7B → Wide DSL 특화 모델

사용법:
  uv run python -m poc1.finetune.train_local
  uv run python -m poc1.finetune.train_local --model Qwen/Qwen2.5-3B-Instruct
"""
import argparse
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

TRAIN_FILE = Path("poc1/finetune/train.jsonl")
OUTPUT_DIR = Path("poc1/finetune/model_output")
MODEL_ID   = "Qwen/Qwen2.5-1.5B-Instruct"  # 기본값

LORA_CONFIG = dict(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

TRAIN_CONFIG = dict(
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,   # effective batch = 16
    learning_rate=2e-4,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    fp16=False,
    bf16=True,                        # 4090은 BF16 지원
    logging_steps=10,
    save_steps=100,
    save_total_limit=2,
    optim="adamw_8bit",
    report_to="none",
)


def load_dataset(path: Path, tokenizer):
    from datasets import Dataset
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    # messages → chat template 적용하여 text로 변환
    def apply_template(example):
        text = tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}

    ds = Dataset.from_list(records)
    return ds.map(apply_template, remove_columns=["messages"])


def train(model_id: str, output_dir: Path):
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    log.info(f"모델 로드: {model_id}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_id,
        max_seq_length=1024,
        dtype=None,          # auto (BF16 on 4090)
        load_in_4bit=False,  # 1.5B는 4bit 불필요, 24GB 여유
    )

    log.info("LoRA 적용 중...")
    model = FastLanguageModel.get_peft_model(model, **LORA_CONFIG)
    model.print_trainable_parameters()

    log.info(f"데이터셋 로드: {TRAIN_FILE}")
    dataset = load_dataset(TRAIN_FILE, tokenizer)
    log.info(f"  → {len(dataset)}개 샘플")
    log.info(f"  예시:\n{dataset[0]['text'][:300]}")

    output_dir.mkdir(parents=True, exist_ok=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        args=TrainingArguments(
            output_dir=str(output_dir),
            **TRAIN_CONFIG,
        ),
        max_seq_length=1024,
    )

    log.info("파인튜닝 시작!")
    trainer.train()

    log.info(f"모델 저장: {output_dir}")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # 결과 메타 저장
    meta = {
        "base_model": model_id,
        "output_dir": str(output_dir),
        "n_samples": len(dataset),
        "lora_config": LORA_CONFIG,
        "train_config": TRAIN_CONFIG,
    }
    (output_dir / "train_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False)
    )
    log.info("완료!")
    return output_dir


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL_ID, help="HuggingFace 모델 ID")
    p.add_argument("--output", default=str(OUTPUT_DIR), help="출력 디렉토리")
    args = p.parse_args()

    if not TRAIN_FILE.exists():
        raise SystemExit(f"학습 데이터 없음: {TRAIN_FILE}\n먼저 uv run python -m poc1.finetune.data_gen 실행")

    n = sum(1 for _ in open(TRAIN_FILE))
    log.info(f"학습 샘플: {n}개")

    out = train(args.model, Path(args.output))
    print(f"\n파인튜닝 완료: {out}")
    print("평가: uv run python -m poc1.main --model local")


if __name__ == "__main__":
    main()
