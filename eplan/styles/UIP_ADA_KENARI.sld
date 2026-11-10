<?xml version="1.0" encoding="utf-8"?>
<StyledLayerDescriptor version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<NamedLayer>
		<Name>UIP_ADA_KENARI</Name>
		<UserStyle>
			<Title>UIP_ADA_KENARI</Title>
			<FeatureTypeStyle>
				<Rule>
					<Name>0</Name>
					<Title>KADEME_HATTI</Title>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>ada_kenari_cizgi_tip</ogc:PropertyName>
							<ogc:Literal>4</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>5000</MaxScaleDenominator>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">0.3528</CssParameter>
						</Stroke>
					</LineSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>ONERILEN</Title>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>ada_kenari_cizgi_tip</ogc:PropertyName>
							<ogc:Literal>0</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>5000</MaxScaleDenominator>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
							</CssParameter>
						</Stroke>
						<PerpendicularOffset>
							<ogc:Mul>
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
								<ogc:Literal>0.5</ogc:Literal>
							</ogc:Mul>
						</PerpendicularOffset>
					</LineSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>KORUNAN</Title>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>ada_kenari_cizgi_tip</ogc:PropertyName>
							<ogc:Literal>1</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>5000</MaxScaleDenominator>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
							</CssParameter>
							<CssParameter name="stroke-dasharray">0.575 0.575</CssParameter>
						</Stroke>
						<PerpendicularOffset>
							<ogc:Mul>
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
								<ogc:Literal>0.5</ogc:Literal>
							</ogc:Mul>
						</PerpendicularOffset>
					</LineSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>DUZELTILEN</Title>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>ada_kenari_cizgi_tip</ogc:PropertyName>
							<ogc:Literal>2</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>5000</MaxScaleDenominator>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
							</CssParameter>
							<CssParameter name="stroke-dasharray">2 0.6</CssParameter>
						</Stroke>
						<PerpendicularOffset>
							<ogc:Mul>
								<ogc:PropertyName>cizgi_kalinligi</ogc:PropertyName>
								<ogc:Literal>0.5</ogc:Literal>
							</ogc:Mul>
						</PerpendicularOffset>
					</LineSymbolizer>
				</Rule>
				<Rule>
					<Name>0</Name>
					<Title>IFRAZ_HATTI</Title>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>ada_kenari_cizgi_tip</ogc:PropertyName>
							<ogc:Literal>3</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>5000</MaxScaleDenominator>
					<LineSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Stroke>
							<CssParameter name="stroke">#000000</CssParameter>
							<CssParameter name="stroke-width">0.3528</CssParameter>
							<CssParameter name="stroke-dasharray">2 2</CssParameter>
						</Stroke>
					</LineSymbolizer>
				</Rule>
			</FeatureTypeStyle>
		</UserStyle>
	</NamedLayer>
</StyledLayerDescriptor>