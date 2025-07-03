package org.example.adapter;

import org.example.model.DocumentType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

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
