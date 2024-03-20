from transformers import PreTrainedModel, AutoModel, AutoConfig

class Dot(PreTrainedModel):
    def __init__(
        self,
        encoder: PreTrainedModel,
        config: AutoConfig,
        mode : int = 'cls'
    ):
        super().__init__(config)
        self.encoder = encoder
    
        self.agg = lambda x: x.mean(dim=1) if mode == 'cls' else x[:,0,:]
    
    def encode(self, **text):
        return self.agg(self.encoder(**text)[0])

    def forward(self, loss, queries, docs_batch, labels=None):
        """Compute the loss given (queries, docs, labels)"""
        queries = {k: v.to(self.encoder.device) for k, v in queries.items()}
        docs_batch = {k: v.to(self.encoder.device) for k, v in docs_batch.items()}
        labels = labels.to(self.encoder.device) if labels is not None else None
        q_reps = self.encode(**queries)
        docs_batch_rep = self.encode(**docs_batch)
        if labels is None:
            output = loss(q_reps, docs_batch_rep)
        else:
            output = loss(q_reps, docs_batch_rep, labels)
        return output

    def save_pretrained(self, model_dir):
        """Save both query and document encoder"""
        self.config.save_pretrained(model_dir)
        self.encoder.save_pretrained(model_dir)
    
    def load_state_dict(self, model_dir):
        """Load state dict from a directory"""
        return self.encoder.load_state_dict(AutoModel.from_pretrained(model_dir).state_dict())

    @classmethod
    def from_pretrained(cls, model_dir_or_name):
        """Load encoder from a directory"""
        config = AutoConfig.from_pretrained(model_dir_or_name)
        encoder = AutoModel.from_pretrained(model_dir_or_name)
        return cls(encoder, config)