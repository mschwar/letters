from apps.worker.extraction import extract_metadata


def test_extract_metadata_date() -> None:
    text = "Letter dated 2020-05-04 from the Universal House of Justice"
    metadata = extract_metadata(text)
    assert metadata.document_date == "2020-05-04"
    assert metadata.source_name == "Universal House of Justice"
    assert metadata.summary_one_sentence is not None
