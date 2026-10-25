"""Optional local inference process. It never downloads models or reads API keys."""
import json
import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"


def main():
    import torch
    from transformers import AutoModel, AutoTokenizer

    payload = json.load(sys.stdin)
    name = payload["model"]
    tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=True, token=False, trust_remote_code=False)
    model = AutoModel.from_pretrained(name, local_files_only=True, token=False, trust_remote_code=False)
    model.eval()
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.manual_seed(0)
    texts = payload["prototypes"] + payload["texts"]
    vectors, tokens, calls = [], 0, 0
    with torch.inference_mode():
        for start in range(0, len(texts), 16):
            batch = tokenizer(texts[start:start+16], padding=True, truncation=True, max_length=256, return_tensors="pt")
            tokens += int(batch["attention_mask"].sum())
            hidden = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            vectors.append(torch.nn.functional.normalize(pooled, dim=1))
            calls += 1
    vectors = torch.cat(vectors)
    count = len(payload["prototypes"])
    scores = vectors[count:] @ vectors[:count].T
    json.dump({"scores":scores.tolist(), "input_tokens":tokens, "model_calls":calls,
               "model":name},sys.stdout)


if __name__ == "__main__":
    main()
