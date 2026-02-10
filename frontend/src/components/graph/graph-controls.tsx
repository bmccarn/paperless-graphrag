"use client";

import { useState, useEffect } from "react";
import {
	Search,
	Loader2,
	Plus,
	Box,
	Square,
	Palette,
	Maximize,
	Minimize2,
	Maximize2,
	Settings2,
	ChevronUp,
	ChevronDown,
	RotateCcw,
	Focus,
	EyeOff,
	Filter,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
	useGraphStore,
	type ColorByOption,
	type SizeByOption,
} from "@/lib/stores";
import type { GraphOverview } from "@/types";

interface GraphControlsProps {
	overview: GraphOverview | null;
	onSearch: (query: string) => void;
	onTypeFilter: (type: string | null) => void;
	onReset?: () => void;
	onResetView?: () => void;
	isSearching?: boolean;
	entityCount?: number;
	currentLimit?: number;
	maxLimit?: number;
	onLoadMore?: () => void;
	onSetLimit?: (limit: number) => void;
	canLoadMore?: boolean;
	isFullscreen?: boolean;
	onToggleFullscreen?: () => void;
	portalContainer?: HTMLElement | null;
	hiddenNodeCount?: number;
}

export function GraphControls({
	overview,
	onSearch,
	onTypeFilter,
	onReset,
	onResetView,
	isSearching,
	entityCount,
	currentLimit,
	maxLimit,
	onLoadMore,
	onSetLimit,
	canLoadMore,
	isFullscreen,
	onToggleFullscreen,
	portalContainer,
	hiddenNodeCount,
}: GraphControlsProps) {
	const [controlsExpanded, setControlsExpanded] = useState(false);
	const [customLimit, setCustomLimit] = useState<string>(
		currentLimit?.toString() || "500"
	);
	const {
		filters,
		setFilters,
		resetFilters,
		is3DMode,
		toggle3DMode,
		colorBy,
		setColorBy,
		sizeBy,
		setSizeBy,
		hideIsolatedNodes,
		setHideIsolatedNodes,
		minDegree,
		setMinDegree,
	} = useGraphStore();

	// Sync customLimit with currentLimit when it changes
	useEffect(() => {
		if (currentLimit !== undefined) {
			setCustomLimit(currentLimit.toString());
		}
	}, [currentLimit]);

	// Handle custom limit input change
	const handleCustomLimitChange = (value: string) => {
		setCustomLimit(value);
	};

	// Handle custom limit submission
	const handleCustomLimitSubmit = () => {
		const numValue = parseInt(customLimit, 10);
		if (!isNaN(numValue) && onSetLimit && maxLimit) {
			const clampedValue = Math.max(100, Math.min(numValue, maxLimit));
			onSetLimit(clampedValue);
			setCustomLimit(clampedValue.toString());
		}
	};

	// Handle Enter key in custom limit input
	const handleCustomLimitKeyDown = (
		e: React.KeyboardEvent<HTMLInputElement>
	) => {
		if (e.key === "Enter") {
			handleCustomLimitSubmit();
		}
	};

	return (
		<>
			{/* Desktop Controls - Top Left - z-[60] ensures visibility in fullscreen */}
			<div
				className={`absolute top-2 left-2 md:top-4 md:left-4 bottom-2 md:bottom-4 hidden md:block ${
					isFullscreen ? "z-[60]" : "z-10"
				}`}>
				<div
					className="h-full overflow-y-auto overflow-x-hidden pr-2 flex flex-col gap-2"
					style={{ scrollbarWidth: "thin" }}>
					{/* Search */}
					<div className="flex items-center gap-2 bg-background border rounded-lg p-2">
						{isSearching ? (
							<Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
						) : (
							<Search className="h-4 w-4 text-muted-foreground" />
						)}
						<Input
							placeholder="Search entities..."
							className="h-8 w-48 border-0 focus-visible:ring-0"
							value={filters.searchQuery}
							onChange={(e) => {
								setFilters({ searchQuery: e.target.value });
								onSearch(e.target.value);
							}}
						/>
					</div>

					{/* Entity count indicator with custom limit control */}
					{entityCount !== undefined && (
						<div className="space-y-2">
							<div className="bg-background/90 border rounded-lg px-3 py-1.5 text-xs text-muted-foreground">
								Showing {entityCount} {currentLimit && `/ ${currentLimit}`}{" "}
								entities
							</div>

							{/* Custom entity limit input */}
							<div className="bg-background border rounded-lg p-2 space-y-2">
								<label className="text-xs text-muted-foreground">
									Load Entities:
								</label>
								<div className="flex items-center gap-1">
									<Input
										type="number"
										min="100"
										max={maxLimit}
										value={customLimit}
										onChange={(e) => handleCustomLimitChange(e.target.value)}
										onKeyDown={handleCustomLimitKeyDown}
										className="h-7 w-24 text-xs"
										placeholder="500"
									/>
									<Button
										variant="outline"
										size="sm"
										className="h-7 px-2 text-xs"
										onClick={handleCustomLimitSubmit}>
										Load
									</Button>
								</div>
								{canLoadMore && (
									<Button
										variant="ghost"
										size="sm"
										className="h-6 w-full px-2 text-xs"
										onClick={onLoadMore}>
										<Plus className="h-3 w-3 mr-1" />
										+100 More
									</Button>
								)}
								{maxLimit && (
									<div className="text-[10px] text-muted-foreground">
										Max: {maxLimit}
									</div>
								)}
							</div>
						</div>
					)}

					{/* Type Filter */}
					<div className="bg-background border rounded-lg p-2">
						<Select
							value={filters.entityTypes[0] || "all"}
							onValueChange={(value) => {
								const type = value === "all" ? null : value;
								setFilters({ entityTypes: type ? [type] : [] });
								onTypeFilter(type);
							}}>
							<SelectTrigger className="h-8 w-48">
								<SelectValue placeholder="Filter by type" />
							</SelectTrigger>
							<SelectContent
								className="z-[100]"
								container={portalContainer}>
								<SelectItem value="all">All Types</SelectItem>
								{overview?.entity_types
									.filter(({ type }) => type && type.trim() !== "")
									.map(({ type, count }) => (
										<SelectItem
											key={type}
											value={type}>
											{type} ({count})
										</SelectItem>
									))}
							</SelectContent>
						</Select>
					</div>

					{/* View Mode Toggle (2D/3D) */}
					<div className="bg-background border rounded-lg p-2">
						<div className="flex items-center gap-2">
							<span className="text-xs text-muted-foreground">View:</span>
							<ToggleGroup
								type="single"
								value={is3DMode ? "3d" : "2d"}
								onValueChange={(value: string) => {
									if (value) toggle3DMode();
								}}
								className="gap-1">
								<ToggleGroupItem
									value="2d"
									size="sm"
									className="h-7 px-2 text-xs">
									<Square className="h-3 w-3 mr-1" />
									2D
								</ToggleGroupItem>
								<ToggleGroupItem
									value="3d"
									size="sm"
									className="h-7 px-2 text-xs">
									<Box className="h-3 w-3 mr-1" />
									3D
								</ToggleGroupItem>
							</ToggleGroup>
						</div>
					</div>

					{/* Color By Selector */}
					<div className="bg-background border rounded-lg p-2">
						<div className="flex items-center gap-2">
							<Palette className="h-4 w-4 text-muted-foreground" />
							<Select
								value={colorBy}
								onValueChange={(value: ColorByOption) => setColorBy(value)}>
								<SelectTrigger className="h-8 w-36">
									<SelectValue placeholder="Color by" />
								</SelectTrigger>
								<SelectContent
									className="z-[100]"
									container={portalContainer}>
									<SelectItem value="type">Color by Type</SelectItem>
									<SelectItem value="community">Color by Community</SelectItem>
								</SelectContent>
							</Select>
						</div>
					</div>

					{/* Size By Selector */}
					<div className="bg-background border rounded-lg p-2">
						<div className="flex items-center gap-2">
							<Maximize className="h-4 w-4 text-muted-foreground" />
							<Select
								value={sizeBy}
								onValueChange={(value: SizeByOption) => setSizeBy(value)}>
								<SelectTrigger className="h-8 w-36">
									<SelectValue placeholder="Size by" />
								</SelectTrigger>
								<SelectContent
									className="z-[100]"
									container={portalContainer}>
									<SelectItem value="uniform">Uniform Size</SelectItem>
									<SelectItem value="degree">Size by Connections</SelectItem>
								</SelectContent>
							</Select>
						</div>
					</div>

					{/* Hide Isolated Nodes Toggle */}
					<div className="bg-background border rounded-lg p-2">
						<div className="flex items-center justify-between gap-2">
							<label className="text-xs text-muted-foreground flex items-center gap-1 cursor-pointer" htmlFor="hide-isolated">
								<EyeOff className="h-3 w-3" />
								Hide isolated{hiddenNodeCount ? ` (${hiddenNodeCount})` : ''}
							</label>
							<Switch
								id="hide-isolated"
								checked={hideIsolatedNodes}
								onCheckedChange={setHideIsolatedNodes}
							/>
						</div>
					</div>

					{/* Min Degree Slider */}
					<div className="bg-background border rounded-lg p-2 space-y-2">
						<div className="flex items-center justify-between">
							<label className="text-xs text-muted-foreground flex items-center gap-1">
								<Filter className="h-3 w-3" />
								Min connections
							</label>
							<span className="text-xs font-mono text-muted-foreground">{minDegree}</span>
						</div>
						<Slider
							min={0}
							max={10}
							step={1}
							value={[minDegree]}
							onValueChange={([val]) => setMinDegree(val)}
							className="w-full"
						/>
					</div>

					{/* Reset View Button */}
					{onResetView && (
						<Button
							variant="outline"
							size="sm"
							className="h-8"
							onClick={onResetView}>
							<Focus className="h-4 w-4 mr-2" />
							Reset View
						</Button>
					)}

					{/* Reset Filters Button */}
					<Button
						variant="outline"
						size="sm"
						className="h-8"
						onClick={() => {
							resetFilters();
							onReset?.();
						}}>
						<RotateCcw className="h-4 w-4 mr-2" />
						Reset Filters
					</Button>

					{/* Fullscreen Toggle */}
					{onToggleFullscreen && (
						<Button
							variant="outline"
							size="sm"
							className="h-8"
							onClick={onToggleFullscreen}>
							{isFullscreen ? (
								<>
									<Minimize2 className="h-4 w-4 mr-2" />
									Exit Fullscreen
								</>
							) : (
								<>
									<Maximize2 className="h-4 w-4 mr-2" />
									Fullscreen
								</>
							)}
						</Button>
					)}
				</div>
			</div>

			{/* Mobile Controls - Bottom Panel */}
			<div
				className={`${
					isFullscreen ? "fixed" : "absolute"
				} bottom-0 left-0 right-0 z-[51] md:hidden`}
				style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
				{/* Collapsed State - Show toggle and key controls */}
				<div className="flex items-center justify-between gap-2 p-2 bg-background/95 backdrop-blur-md border-t">
					{/* Entity count */}
					{entityCount !== undefined && (
						<div className="text-xs text-muted-foreground px-2">
							{entityCount} entities
						</div>
					)}

					<div className="flex items-center gap-2 ml-auto">
						{/* Quick Fullscreen */}
						{onToggleFullscreen && (
							<Button
								variant="ghost"
								size="sm"
								className="h-9 w-9 p-0"
								onClick={onToggleFullscreen}>
								{isFullscreen ? (
									<Minimize2 className="h-4 w-4" />
								) : (
									<Maximize2 className="h-4 w-4" />
								)}
							</Button>
						)}

						{/* 2D/3D Quick Toggle */}
						<Button
							variant="ghost"
							size="sm"
							className="h-9 px-3 text-xs"
							onClick={toggle3DMode}>
							{is3DMode ? (
								<>
									<Box className="h-4 w-4 mr-1" />
									3D
								</>
							) : (
								<>
									<Square className="h-4 w-4 mr-1" />
									2D
								</>
							)}
						</Button>

						{/* Expand Controls */}
						<Button
							variant="outline"
							size="sm"
							className="h-9 px-3"
							onClick={() => setControlsExpanded(!controlsExpanded)}>
							<Settings2 className="h-4 w-4 mr-1" />
							{controlsExpanded ? (
								<ChevronDown className="h-3 w-3" />
							) : (
								<ChevronUp className="h-3 w-3" />
							)}
						</Button>
					</div>
				</div>

				{/* Expanded Controls Panel */}
				{controlsExpanded && (
					<div className="p-3 bg-background border-t space-y-3 max-h-[50vh] overflow-y-auto">
						{/* Search */}
						<div className="flex items-center gap-2 bg-secondary/50 rounded-lg p-2">
							{isSearching ? (
								<Loader2 className="h-4 w-4 text-muted-foreground animate-spin shrink-0" />
							) : (
								<Search className="h-4 w-4 text-muted-foreground shrink-0" />
							)}
							<Input
								placeholder="Search entities..."
								className="h-9 border-0 focus-visible:ring-0 bg-transparent"
								value={filters.searchQuery}
								onChange={(e) => {
									setFilters({ searchQuery: e.target.value });
									onSearch(e.target.value);
								}}
							/>
						</div>

						{/* Custom entity limit control */}
						<div className="space-y-2 bg-secondary/30 rounded-lg p-3">
							<label className="text-xs text-muted-foreground">
								Load Entities:
							</label>
							<div className="flex items-center gap-2">
								<Input
									type="number"
									min="100"
									max={maxLimit}
									value={customLimit}
									onChange={(e) => handleCustomLimitChange(e.target.value)}
									onKeyDown={handleCustomLimitKeyDown}
									className="h-10 flex-1 text-sm"
									placeholder="500"
								/>
								<Button
									variant="outline"
									size="sm"
									className="h-10 px-4"
									onClick={handleCustomLimitSubmit}>
									Load
								</Button>
							</div>
							{canLoadMore && (
								<Button
									variant="ghost"
									size="sm"
									className="w-full h-9"
									onClick={onLoadMore}>
									<Plus className="h-4 w-4 mr-2" />
									Load 100 More
								</Button>
							)}
							{maxLimit && currentLimit && (
								<div className="text-xs text-muted-foreground text-center">
									Current: {currentLimit} | Max: {maxLimit}
								</div>
							)}
						</div>

						{/* Type Filter */}
						<div className="space-y-1.5">
							<label className="text-xs text-muted-foreground">
								Filter by Type
							</label>
							<Select
								value={filters.entityTypes[0] || "all"}
								onValueChange={(value) => {
									const type = value === "all" ? null : value;
									setFilters({ entityTypes: type ? [type] : [] });
									onTypeFilter(type);
								}}>
								<SelectTrigger className="h-10 w-full">
									<SelectValue placeholder="Filter by type" />
								</SelectTrigger>
								<SelectContent
									className="z-[100]"
									container={portalContainer}>
									<SelectItem value="all">All Types</SelectItem>
									{overview?.entity_types
										.filter(({ type }) => type && type.trim() !== "")
										.map(({ type, count }) => (
											<SelectItem
												key={type}
												value={type}>
												{type} ({count})
											</SelectItem>
										))}
								</SelectContent>
							</Select>
						</div>

						{/* View Options Row */}
						<div className="grid grid-cols-2 gap-2">
							{/* Color By */}
							<div className="space-y-1.5">
								<label className="text-xs text-muted-foreground flex items-center gap-1">
									<Palette className="h-3 w-3" /> Color
								</label>
								<Select
									value={colorBy}
									onValueChange={(value: ColorByOption) => setColorBy(value)}>
									<SelectTrigger className="h-10 w-full">
										<SelectValue />
									</SelectTrigger>
									<SelectContent
										className="z-[100]"
										container={portalContainer}>
										<SelectItem value="type">Type</SelectItem>
										<SelectItem value="community">Community</SelectItem>
									</SelectContent>
								</Select>
							</div>

							{/* Size By */}
							<div className="space-y-1.5">
								<label className="text-xs text-muted-foreground flex items-center gap-1">
									<Maximize className="h-3 w-3" /> Size
								</label>
								<Select
									value={sizeBy}
									onValueChange={(value: SizeByOption) => setSizeBy(value)}>
									<SelectTrigger className="h-10 w-full">
										<SelectValue />
									</SelectTrigger>
									<SelectContent
										className="z-[100]"
										container={portalContainer}>
										<SelectItem value="uniform">Uniform</SelectItem>
										<SelectItem value="degree">Connections</SelectItem>
									</SelectContent>
								</Select>
							</div>
						</div>

						{/* Hide Isolated Nodes Toggle */}
						<div className="flex items-center justify-between bg-secondary/30 rounded-lg p-3">
							<label className="text-xs text-muted-foreground flex items-center gap-1" htmlFor="hide-isolated-mobile">
								<EyeOff className="h-3 w-3" />
								Hide isolated{hiddenNodeCount ? ` (${hiddenNodeCount})` : ''}
							</label>
							<Switch
								id="hide-isolated-mobile"
								checked={hideIsolatedNodes}
								onCheckedChange={setHideIsolatedNodes}
							/>
						</div>

						{/* Min Degree Slider */}
						<div className="bg-secondary/30 rounded-lg p-3 space-y-2">
							<div className="flex items-center justify-between">
								<label className="text-xs text-muted-foreground flex items-center gap-1">
									<Filter className="h-3 w-3" />
									Min connections
								</label>
								<span className="text-xs font-mono text-muted-foreground">{minDegree}</span>
							</div>
							<Slider
								min={0}
								max={10}
								step={1}
								value={[minDegree]}
								onValueChange={([val]) => setMinDegree(val)}
								className="w-full"
							/>
						</div>

						{/* Reset Buttons Row */}
						<div className="grid grid-cols-2 gap-2">
							{/* Reset View Button */}
							{onResetView && (
								<Button
									variant="outline"
									size="sm"
									className="h-10"
									onClick={onResetView}>
									<Focus className="h-4 w-4 mr-2" />
									Reset View
								</Button>
							)}

							{/* Reset Filters Button */}
							<Button
								variant="outline"
								size="sm"
								className={onResetView ? "h-10" : "w-full h-10"}
								onClick={() => {
									resetFilters();
									onReset?.();
								}}>
								<RotateCcw className="h-4 w-4 mr-2" />
								Reset Filters
							</Button>
						</div>
					</div>
				)}
			</div>
		</>
	);
}
