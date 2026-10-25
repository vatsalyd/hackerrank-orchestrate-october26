"""Download public local model weights without authentication or participant data."""
import argparse
from transformers import AutoModel, AutoTokenizer

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',default='sentence-transformers/all-MiniLM-L6-v2')
args=parser.parse_args()
AutoTokenizer.from_pretrained(args.model,token=False,trust_remote_code=False)
AutoModel.from_pretrained(args.model,token=False,trust_remote_code=False)
print(f'Cached public weights for {args.model}; local inference needs no API key.')
