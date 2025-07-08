package org.example.model.publication;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.AuctionTypeAdapter;
import org.example.adapter.BusinessTypeAdapter;
import org.example.adapter.ContractMarketAgreementTypeAdapter;
import org.example.adapter.CurveTypeAdapter;
import org.example.model.common.*;

// Time Series class
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class TimeSeries {

  @XmlElement(name = "mRID")
  private String mRID;

  @XmlElement(name = "auction.type")
  @XmlJavaTypeAdapter(AuctionTypeAdapter.class)
  private AuctionType auctionType;

  @XmlElement(name = "businessType")
  @XmlJavaTypeAdapter(BusinessTypeAdapter.class)
  private BusinessType businessType;

  @XmlElement(name = "in_Domain.mRID")
  private DomainMRID inDomainMRID;

  @XmlElement(name = "out_Domain.mRID")
  private DomainMRID outDomainMRID;

  @XmlElement(name = "contract_MarketAgreement.type")
  @XmlJavaTypeAdapter(ContractMarketAgreementTypeAdapter.class)
  private ContractMarketAgreementType contractMarketAgreementType;

  @XmlElement(name = "currency_Unit.name")
  private String currencyUnitName;

  @XmlElement(name = "price_Measure_Unit.name")
  private String priceMeasureUnitName;

  @XmlElement(name = "curveType")
  @XmlJavaTypeAdapter(CurveTypeAdapter.class)
  private CurveType curveType;

  @XmlElement(name = "Period")
  private Period period;
}
