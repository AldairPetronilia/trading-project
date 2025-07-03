package org.example.adapter;

import org.example.model.common.MarketRoleType;
import org.example.model.common.ProcessType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class ProcessTypeAdapter extends XmlAdapter<String, ProcessType> {

    @Override
    public ProcessType unmarshal(String code) {
        return ProcessType.fromCode(code);
    }

    @Override
    public String marshal(ProcessType type) { return type.getCode(); }
}
