package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.ContractMarketAgreementType;

public class ContractMarketAgreementTypeAdapter
    extends XmlAdapter<String, ContractMarketAgreementType> {
  @Override
  public ContractMarketAgreementType unmarshal(String code) {
    return ContractMarketAgreementType.fromCode(code);
  }

  @Override
  public String marshal(ContractMarketAgreementType type) {
    return type.getCode();
  }
}
