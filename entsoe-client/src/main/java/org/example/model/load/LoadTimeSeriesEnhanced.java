package org.example.model.load;

import static org.example.model.load.GLMarketDocument.XML_NAMESPACE;

import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.BusinessTypeAdapter;
import org.example.adapter.CurveTypeAdapter;
import org.example.adapter.ObjectAggregationAdapter;
import org.example.model.common.AreaCode;
import org.example.model.common.BusinessType;
import org.example.model.common.CurveType;
import org.example.model.common.DomainMRID;

// Enhanced LoadTimeSeries with ObjectAggregation enum
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class LoadTimeSeriesEnhanced {

  @XmlElement(name = "mRID", namespace = XML_NAMESPACE)
  private String mRID;

  @XmlElement(name = "businessType", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(BusinessTypeAdapter.class)
  private BusinessType businessType;

  @XmlElement(name = "objectAggregation", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(ObjectAggregationAdapter.class)
  private ObjectAggregation objectAggregation;

  @XmlElement(name = "outBiddingZone_Domain.mRID", namespace = XML_NAMESPACE)
  private DomainMRID outBiddingZoneDomainMRID;

  @XmlElement(name = "quantity_Measure_Unit.name", namespace = XML_NAMESPACE)
  private String quantityMeasureUnitName;

  @XmlElement(name = "curveType", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(CurveTypeAdapter.class)
  private CurveType curveType;

  @XmlElement(name = "Period", namespace = XML_NAMESPACE)
  private List<LoadPeriod> periods;

  // Helper method to get area code
  public AreaCode getOutBiddingZoneAreaCode() {
    return outBiddingZoneDomainMRID != null ? outBiddingZoneDomainMRID.getAreaCode() : null;
  }
}
