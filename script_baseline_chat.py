import jsonlines
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os

import warnings

warnings.filterwarnings("ignore")

DATA_DIR = "data"
EVAL_FILE = os.path.join(DATA_DIR, "eval_questions.jsonl")
BASE_MODEL = "microsoft/phi-1_5"  # CPU friendly


def load_eval_questions():
    questions = []
    with jsonlines.open(EVAL_FILE, "r") as reader:
        for l in reader:
            questions.append(l["question"])
    return questions


def chat(model, tokenizer, question):
    """Generate response for a given question."""
    prompt = f"Answer the following question clearly and concisely:\n{question}\nAnswer:"
    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():  # tells PyTorch: Don't track gradients
        # Normally, PyTorch tracks all operations on tensors to compute gradients for training neural networks (backpropagation).
        # When you are only running inference (making predictions, not training), you don’t need gradients.
        output_ids = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=True,  # enable sampling
            temperature=0.7,
            top_p=0.9,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )

    response = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Remove prompt from response
    response = response.replace(prompt, "").strip()
    # output_ids[0] → first (and only) sequence in the batch
    # skip_special_tokens=True removes things like: <eos>, <pad>
    return response


def run_baseline_evaluation():
    print("\nLoading base model...\n\n")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    # tokenizer - Load the text-to-numbers converter that was trained alongside this model.
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)
    # model - Load the actual neural network weights of the language model.

    questions = load_eval_questions()

    print("\n===== Baseline Response (Before Finetunning) =====\n\n")

    for q in questions:
        print(f"Question: {q}\n")
        answer = chat(model, tokenizer, q)
        print(f"Model's Final Response: {answer}\n\n")
        print("-" * 60)


run_baseline_evaluation()