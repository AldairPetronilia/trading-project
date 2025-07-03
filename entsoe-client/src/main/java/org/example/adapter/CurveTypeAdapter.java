package org.example.adapter;

import org.example.model.common.CurveType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class CurveTypeAdapter extends XmlAdapter<String, CurveType> {
    @Override
    public CurveType unmarshal(String code) {
        return CurveType.fromCode(code);
    }

    @Override
    public String marshal(CurveType type) {
        return type.getCode();
    }
}
