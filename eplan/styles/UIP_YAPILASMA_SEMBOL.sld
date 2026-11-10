<?xml version="1.0" encoding="utf-8"?>
<StyledLayerDescriptor version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<NamedLayer>
		<Name>UIP_YAPILASMA_SEMBOL</Name>
		<UserStyle>
			<Title>UIP_YAPILASMA_SEMBOL</Title>
			<FeatureTypeStyle>
				<Rule>
					<Title>UIP_YAPILASMA_SEMBOL</Title>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>2000</MaxScaleDenominator>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>dairemi</ogc:PropertyName>
							<ogc:Literal>1</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Label>(</Label>
						<Font>
							<CssParameter name="font-family">ESRI Default Marker</CssParameter>
							<CssParameter name="font-size">
								<!-- <ogc:PropertyName>fontbuyukluk</ogc:PropertyName> -->
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
					<TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Label>
							<ogc:PropertyName>taksyazi</ogc:PropertyName>
						</Label>
						<Font>
							<CssParameter name="font-family">DejaVu Sans</CssParameter>
							<CssParameter name="font-size">
								<!-- <ogc:PropertyName>fontbuyukluk3</ogc:PropertyName> -->
								<ogc:Literal>4</ogc:Literal>
							</CssParameter>
							<CssParameter name="font-style">normal</CssParameter>
						</Font>
						<LabelPlacement>
							<PointPlacement>
								<AnchorPoint>
									<AnchorPointX>0.5</AnchorPointX>
									<AnchorPointY>-0.4</AnchorPointY>
								</AnchorPoint>
							</PointPlacement>
						</LabelPlacement>
						<Fill>
							<CssParameter name="fill">#000000</CssParameter>
						</Fill>
						<VendorOption name="conflictResolution">false</VendorOption>
						<VendorOption name="underlineText">true</VendorOption>
					</TextSymbolizer>
					<TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Label>
							<ogc:PropertyName>kaksyazi</ogc:PropertyName>
						</Label>
						<Font>
							<CssParameter name="font-family">DejaVu Sans</CssParameter>
							<CssParameter name="font-size">
								<!-- <ogc:PropertyName>fontbuyukluk3</ogc:PropertyName> -->
								<ogc:Literal>4</ogc:Literal>
							</CssParameter>
							<CssParameter name="font-style">normal</CssParameter>
						</Font>
						<LabelPlacement>
							<PointPlacement>
								<AnchorPoint>
									<AnchorPointX>0.5</AnchorPointX>
									<AnchorPointY>1.0</AnchorPointY>
								</AnchorPoint>
							</PointPlacement>
						</LabelPlacement>
						<Fill>
							<CssParameter name="fill">#000000</CssParameter>
						</Fill>
						<VendorOption name="conflictResolution">false</VendorOption>
					</TextSymbolizer>
				</Rule>
				<Rule>
					<Title>yazi 2</Title>
					<MinScaleDenominator>0</MinScaleDenominator>
					<MaxScaleDenominator>2000</MaxScaleDenominator>
					<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
						<ogc:PropertyIsEqualTo>
							<ogc:PropertyName>dairemi</ogc:PropertyName>
							<ogc:Literal>0</ogc:Literal>
						</ogc:PropertyIsEqualTo>
					</ogc:Filter>
					<TextSymbolizer uom="http://www.opengeospatial.org/se/units/metre">
						<Label>
							<ogc:PropertyName>yazi</ogc:PropertyName>
						</Label>
						<Font>
							<CssParameter name="font-family">DejaVu Sans</CssParameter>
							<CssParameter name="font-size">
								<!-- <ogc:Mul>
									<ogc:PropertyName>fontbuyukluk2</ogc:PropertyName>
									<ogc:Literal>2</ogc:Literal>
								</ogc:Mul> -->
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
				</Rule>
			</FeatureTypeStyle>
		</UserStyle>
	</NamedLayer>
</StyledLayerDescriptor>