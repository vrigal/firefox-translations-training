#!/usr/bin/env python3.10
import os

from translations_parser.parser import TrainingParser

from tracking.translations_parser.publishers import WandB

os.environ["TASK_ID"] = "djxo3cDTRPqXN9y57CPaKg"
client = WandB(project="720-online", group="ci_djxo3cDTRPqXN9y57CPaKg", name="test")
with open("./djxo3cDTRPqXN9y57CPaKg.log", "r") as f:
    lines = f.readlines()
parser = TrainingParser(logs_iter=iter(lines), publishers=[], log_filter=None)
client.open(parser=parser, resume=True)
parser.run()
try:
    client.publish()
except Exception as e:
    client.close()
    raise e
client.close()
