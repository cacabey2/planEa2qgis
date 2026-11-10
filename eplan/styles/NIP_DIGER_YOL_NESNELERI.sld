<?xml version="1.0" encoding="utf-8"?>
<StyledLayerDescriptor version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<NamedLayer>
		<Name>NIP_DIGER_YOL_NESNELERI</Name>
		<UserStyle>
			<Title>NIP_DIGER_YOL_NESNELERI</Title>
			<FeatureTypeStyle>
				<Rule>
					<Name>0</Name>
					<Title>0</Title>
					<MaxScaleDenominator>80000</MaxScaleDenominator>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>diger_yol_nesne_tip</ogc:PropertyName>
							<ogc:Literal>0</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<PolygonSymbolizer>
						<Fill>
							<CssParameter name="fill">#000000</CssParameter>
						</Fill>
					</PolygonSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>1</Title>
					<MaxScaleDenominator>80000</MaxScaleDenominator>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>diger_yol_nesne_tip</ogc:PropertyName>
							<ogc:Literal>1</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">1</CssParameter>
						</Stroke>
					</LineSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>2</Title>
					<MaxScaleDenominator>80000</MaxScaleDenominator>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>diger_yol_nesne_tip</ogc:PropertyName>
							<ogc:Literal>2</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">1</CssParameter>
						</Stroke>
					</LineSymbolizer>
				</Rule>
			</FeatureTypeStyle>
		</UserStyle>
	</NamedLayer>
</StyledLayerDescriptor>