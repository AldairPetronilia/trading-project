package org.example.adapter;

import org.example.model.common.AreaCode;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class AreaCodeAdapter extends XmlAdapter<String, AreaCode> {
    @Override
    public AreaCode unmarshal(String code) throws Exception {
        return AreaCode.fromCode(code);
    }

    @Override
    public String marshal(AreaCode areaCode) throws Exception {
        return areaCode.getCode();
    }
}
