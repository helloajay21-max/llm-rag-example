"""
LoRA Fine-Tuning Script (Optimized for Tiny 2-Sample Dataset)

This script:

- Loads microsoft/phi-1_5
- Loads your 2-sample train.jsonl
- Applies LoRA using PEFT (strong alpha for small dataset)
- Trains for many epochs to memorize answers
- Saves adapter weights to models/adapters/lora_acme/
"""

import os
import jsonlines
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments
)
import torch
from peft import LoraConfig, get_peft_model

import warnings

warnings.filterwarnings('ignore')

# --- CONFIG ---
BASE_MODEL = "microsoft/phi-1_5"
DATA_PATH = "data/train.jsonl"
OUTPUT_DIR = "models/adapters/lora_acme"

BATCH_SIZE = 1  # CPU-friendly, This means the model sees 1 training example at a time before updating its internal calculations (gradients).
GRAD_ACCUM = 4  # effective batch size = 4
'''
“Gradient accumulation” means the model collects gradients over 4 batches before updating its weights.
So, even though BATCH_SIZE is 1, the model acts as if it saw 4 examples at once (effective batch size = 4).
This helps stabilize training and simulates a larger batch size without needing more memory.
'''
EPOCHS = 10  # VERY IMPORTANT: small dataset → many epochs
'''
An “epoch” is one full pass through your entire dataset.
With a tiny dataset, you want the model to see the data many times, so you use more epochs.
'''
LR = 2e-4
'''
“Learning rate” (LR) controls how big each update step is when the model learns.
2e-4 means 0.0002 (a small step size), which helps the model learn steadily without overshooting.
'''
MAX_LENGTH = 128  # small input, faster training
'''
This limits the maximum number of tokens (words/pieces of words) in each input.
Shorter inputs make training faster and use less memory.
'''


def load_training_dataset():
    return load_dataset("json", data_files=DATA_PATH)


def tokenize(example, tokenizer):
    """
    Training prompt format:
    Instruction: <question>
    Response: <answer>
    """
    prompt = f"Instruction: {example['instruction']}\nResponse: {example['output']}"

    tokens = tokenizer(
        prompt,
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length"
    )
    tokens["labels"] = tokens["input_ids"].copy()
    # input_ids: The numbers representing your input text
    # labels:The numbers the model should try to predict
    return tokens


def main():
    print("\n=== Loading base model (CPU)… ===")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token  # When you need padding, just reuse the EOS token(<|endoftext|>).

    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)

    print("\n=== Loading dataset… ===")
    dataset = load_training_dataset()

    print("Tokenizing samples…")
    tokenized = dataset.map(lambda ex: tokenize(ex, tokenizer), batched=False)

    # --- LoRA CONFIG (strong adapter for tiny dataset) ---
    print("\n=== Applying LoRA ===")
    lora_config = LoraConfig(
        r=8,  # Rank of the LoRA adapter
        lora_alpha=128,  # Scaling factor applied to LoRA updates -
        # lora_alpha: How strongly the adapter influences the model
        # 128 (large): Adapter can quickly learn and “memorize” data
        target_modules=["Wqkv", "out_proj", "fc1", "fc2"],
        # | Module     | Role                                                                       |
        # | ---------- | ---------------------------------------------------------------------------|
        # | `Wqkv`     | The Attention input wires (Query, Key, Value - decides what to focus on)   |
        # | `out_proj` | The Attention output wire (combines the focused info)                      |
        # | `fc1`      | FFN expansion layer -> The Thinking layer input                            |
        # | `fc2`      | FFN contraction layer -> The Thinking layer output                         |

        lora_dropout=0.05,
        # Randomly drops 5% of LoRA activations during training
        bias="none",
        # Do not train bias terms, Only train LoRA matrices
        task_type="CAUSAL_LM"
        # Mandatory for text generation models. | Models that predict next token (GPT-style)
    )

    model = get_peft_model(model, lora_config)  # Base model weights are frozen, LoRA layers are inserted
    model.print_trainable_parameters()

    # --- TRAINING ---
    print("\n=== Starting Training… ===")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,  # Final LoRA adapter is saved here manually later
        per_device_train_batch_size=BATCH_SIZE,  # How many samples the model sees at once
        gradient_accumulation_steps=GRAD_ACCUM,  # Run 4 forward passes, Accumulate gradients, Apply one optimizer step
        num_train_epochs=EPOCHS,  # Model sees the entire dataset 40 times
        learning_rate=LR,  # Step size for LoRA weight updates
        fp16=False,
        # Half Precision (16-bit) | Pros: Uses less memory, faster training | Cons: Less precise, can cause training instability
        bf16=False,
        # Brain Floating Point (16-bit but smarter) | Pros: Better range than fp16, less precision loss | Cons: Not supported on all hardware
        # Full 32-bit precision (default when both are False)
        logging_steps=10,  # Print training loss every 10 steps, Confirm training is happening, Observe loss going down
        save_strategy="no",  # do not save checkpoints every epoch
        report_to="none"  # Disable reporting to: TensorBoard, MLflow; Keep things simple & local
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    # The data collator’s job is to take individual tokenized examples and turn them into a properly padded
    # batch that the model can train on, using the correct language-modeling rules.

    trainer.train()

    print("\n=== Saving LoRA adapter… ===")
    model.save_pretrained(OUTPUT_DIR)

    print(f"\n🎉 LoRA fine-tuning complete! Adapter saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
