import json

from config import settings
from ml_core.models.cv_ner import CVNerExtractor


def test_cv_ner_known_example():
    with open(settings.m5_id2tag_json) as f:
        id2tag = {int(k): v for k, v in json.load(f).items()}
    extractor = CVNerExtractor(model_dir=settings.model5_path, id2tag=id2tag)
    extractor.load()
    result = extractor.infer("TECHNICALSKILLS SpringMVC , Hibernate , JDBC , Java , J2EE")
    assert isinstance(result["skills"], list)
    assert isinstance(result["certifications"], list)
