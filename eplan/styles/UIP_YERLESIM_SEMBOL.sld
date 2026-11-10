<?xml version="1.0" encoding="utf-8"?>
<StyledLayerDescriptor version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>UIP_YERLESIM_SEMBOL</Name>
    <UserStyle>
      <Title>UIP_YERLESIM_SEMBOL</Title>
      <FeatureTypeStyle>
        <Rule>
          <Title>UIP_YERLESIM_SEMBOL</Title>
          <!--MinScaleDenominator>0</MinScaleDenominator-->
          <MaxScaleDenominator>2000</MaxScaleDenominator>
          <TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
            <!--yazi-->
            <Label>
              <ogc:PropertyName>yazi</ogc:PropertyName>
            </Label>
            <Font>
              <CssParameter name="font-family">DejaVu Sans</CssParameter>
              <CssParameter name="font-size">
                <!--ogc:Mul>
                  <ogc:PropertyName>yazi_buyukluk</ogc:PropertyName>
                  <ogc:Literal>1.5</ogc:Literal>       
                </ogc:Mul-->
                <ogc:Literal>4</ogc:Literal>       
              </CssParameter>
              <CssParameter name="font-style">normal</CssParameter>
            </Font>
            <LabelPlacement>
              <PointPlacement>
                <AnchorPoint>
                  <AnchorPointX>0.5</AnchorPointX>
                  <AnchorPointY>0.5</AnchorPointY>
                </AnchorPoint>
              </PointPlacement>
            </LabelPlacement>
            <Fill>
              <CssParameter name="fill">#000000</CssParameter>
            </Fill>
            <VendorOption name="conflictResolution">false</VendorOption>
          </TextSymbolizer>
          <TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
            <!--yazi-->
            <Label>(</Label>
            <Font>
              <CssParameter name="font-family">ESRI Default Marker</CssParameter>
              <CssParameter name="font-size">
                <!--ogc:PropertyName>yaricap</ogc:PropertyName-->
                <ogc:Literal>20</ogc:Literal>       
              </CssParameter>
              <CssParameter name="font-style">normal</CssParameter>
            </Font>
            <LabelPlacement>
              <PointPlacement>
                <AnchorPoint>
                  <AnchorPointX>0.5</AnchorPointX>
                  <AnchorPointY>0.5</AnchorPointY>
                </AnchorPoint>
              </PointPlacement>
            </LabelPlacement>
            <Fill>
              <CssParameter name="fill">#000000</CssParameter>
            </Fill>
            <VendorOption name="conflictResolution">false</VendorOption>
          </TextSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>