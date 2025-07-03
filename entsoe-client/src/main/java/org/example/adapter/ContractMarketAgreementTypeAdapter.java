package org.example.adapter;

import org.example.model.ContractMarketAgreementType;

import javax.xml.bind.annotation.adapters.XmlAdapter;

public class ContractMarketAgreementTypeAdapter extends XmlAdapter<String, ContractMarketAgreementType> {
    @Override
    public ContractMarketAgreementType unmarshal(String code) {
        return ContractMarketAgreementType.fromCode(code);
    }

    @Override
    public String marshal(ContractMarketAgreementType type) {
        return type.getCode();
    }
}
