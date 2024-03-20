import torch
import os
import transformers
import logging
from collections import defaultdict
from transformers import Trainer

logger = logging.getLogger(__name__)

LOSS_NAME = "loss.pt"

class ConstrastTrainer(Trainer):
    """Customized Trainer from Huggingface's Trainer"""

    def __init__(self, *args, loss=None, **kwargs) -> None:
        super(ConstrastTrainer, self).__init__(*args, **kwargs)
        self.loss = loss
        self.custom_log = defaultdict(lambda: 0.0)
        self.tokenizer = self.data_collator.tokenizer

    def _maybe_log_save_evaluate(
        self, tr_loss, model, trial, epoch, ignore_keys_for_eval
    ):
        if self.control.should_log:
            log = {}
            for metric in self.customed_log:
                log[metric] = (
                    self._nested_gather(self.custom_log[metric]).mean().item()
                )
                log[metric] = round(
                    (
                        log[metric]
                        / (self.state.global_step - self._globalstep_last_logged)
                        / self.args.gradient_accumulation_steps
                    ),
                    4,
                )
            self.log(log)
            for metric in self.customed_log:
                self.custom_log[metric] -= self.custom_log[metric]
            self.control.should_log = True
        super()._maybe_log_save_evaluate(
            tr_loss, model, trial, epoch, ignore_keys_for_eval
        )

    def _load_optimizer_and_scheduler(self, checkpoint):
        super()._load_optimizer_and_scheduler(checkpoint)
        if checkpoint is None:
            return
        if os.path.join(checkpoint, LOSS_NAME):
            self.loss.load_state_dict(torch.load(os.path.join(checkpoint, LOSS_NAME)))

    def compute_loss(self, model, inputs, return_outputs=False):
        """
        Compute loss
        """
        loss_outputs = model(self.loss, **inputs)
        for log_metric in loss_outputs[-1]:
            self.customed_log[log_metric] += loss_outputs[-1][log_metric]
        components = loss_outputs[:-1]
        if len(components) == 1:
            loss = components[0]
        else:
            loss = sum(components)
        return loss

    def _load_from_checkpoint(self, resume_from_checkpoint, model=None):
        """Load from a checkpoint to continue traning"""
        # Load model from checkpoint
        logger.info("Loading model's weight from %s", resume_from_checkpoint)
        self.model.load_state_dict(
            resume_from_checkpoint
        )