package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.DocumentType;

public class DocumentTypeAdapter extends XmlAdapter<String, DocumentType> {
  @Override
  public DocumentType unmarshal(String code) {
    return DocumentType.fromCode(code);
  }

  @Override
  public String marshal(DocumentType type) {
    return type.getCode();
  }
}
