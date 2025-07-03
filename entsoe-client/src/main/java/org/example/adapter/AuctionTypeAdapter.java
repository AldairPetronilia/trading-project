package org.example.adapter;

import org.example.model.common.AuctionType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class AuctionTypeAdapter extends XmlAdapter<String, AuctionType> {
    @Override
    public AuctionType unmarshal(String code) {
        return AuctionType.fromCode(code);
    }

    @Override
    public String marshal(AuctionType type) {
        return type.getCode();
    }
}
