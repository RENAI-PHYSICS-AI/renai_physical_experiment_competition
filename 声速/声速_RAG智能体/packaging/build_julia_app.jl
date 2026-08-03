using Pkg

const PACKAGING_DIR = @__DIR__
const SOURCE_DIR = joinpath(PACKAGING_DIR, "packagecompiler_source")
const BUILD_ENV = get(
    ENV,
    "SOUND_SPEED_JULIA_BUILD_DIR",
    joinpath(PACKAGING_DIR, "julia_build"),
)
const OUTPUT_DIR = get(
    ENV,
    "SOUND_SPEED_JULIA_OUTPUT_DIR",
    joinpath(PACKAGING_DIR, "julia_app"),
)
const ASSET_DIR = joinpath(PACKAGING_DIR, "assets")
const FONT_SOURCE = joinpath(ASSET_DIR, "NotoSansCJKsc-Regular.otf")
const FONT_LICENSE = joinpath(ASSET_DIR, "Noto-CJK-LICENSE.txt")
const WEB_SOURCE = normpath(
    joinpath(
        PACKAGING_DIR,
        "..",
        "..",
        "声速测量可视化实验说明",
        "声速四种方法_Julia综合可视化方案",
        "web",
        "web.jl",
    ),
)

isfile(WEB_SOURCE) || error("找不到 Julia 网页实验源文件：$(WEB_SOURCE)")
isfile(FONT_SOURCE) || error("找不到内置中文字体：$(FONT_SOURCE)")
mkpath(joinpath(SOURCE_DIR, "src"))
cp(WEB_SOURCE, joinpath(SOURCE_DIR, "src", "web_impl.jl"); force = true)

Pkg.activate(SOURCE_DIR)
Pkg.instantiate()

Pkg.activate(BUILD_ENV)
Pkg.add(PackageSpec(name = "PackageCompiler", version = "2"))
Pkg.develop(path = SOURCE_DIR)
Pkg.instantiate()

using PackageCompiler
using SoundSpeedWebRuntime

create_app(
    SOURCE_DIR,
    OUTPUT_DIR;
    executables = ["SoundSpeedWebRuntime" => "julia_main"],
    force = true,
    incremental = true,
    include_lazy_artifacts = true,
)

font_dir = joinpath(OUTPUT_DIR, "share", "sound_speed", "fonts")
mkpath(font_dir)
cp(FONT_SOURCE, joinpath(font_dir, basename(FONT_SOURCE)); force = true)
isfile(FONT_LICENSE) && cp(
    FONT_LICENSE,
    joinpath(font_dir, basename(FONT_LICENSE));
    force = true,
)

# WGLMakie loads shader source files at render time. Copy them beside the
# compiled runtime so the executable never refers to the build machine depot.
wgl_asset_source = Base.pkgdir(SoundSpeedWebRuntime.WGLMakie, "assets")
wgl_asset_dir = joinpath(OUTPUT_DIR, "share", "sound_speed", "wglmakie_assets")
isdir(wgl_asset_dir) && rm(wgl_asset_dir; recursive = true, force = true)
cp(wgl_asset_source, wgl_asset_dir; force = true)

println("Sound-speed Julia app created at $(OUTPUT_DIR)")
