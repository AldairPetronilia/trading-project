package org.example.adapter;

import org.example.model.common.MarketRoleType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class MarketRoleTypeAdapter extends XmlAdapter<String, MarketRoleType> {
    @Override
    public MarketRoleType unmarshal(String code) {
        return MarketRoleType.fromCode(code);
    }

    @Override
    public String marshal(MarketRoleType type) {
        return type.getCode();
    }
}
