using Pkg

const PACKAGING_DIR = @__DIR__
const SOURCE_DIR = joinpath(PACKAGING_DIR, "packagecompiler_source")
const BUILD_ENV = joinpath(PACKAGING_DIR, "julia_build")
const OUTPUT_DIR = joinpath(PACKAGING_DIR, "julia_app")
const WEB_SOURCE = normpath(
    joinpath(
        PACKAGING_DIR,
        "..",
        "..",
        "李萨如图形可视化实验说明",
        "实验一至四_Julia综合可视化方案",
        "web.jl",
    ),
)

isfile(WEB_SOURCE) || error("找不到 Julia 网页实验源文件：$(WEB_SOURCE)")
cp(WEB_SOURCE, joinpath(SOURCE_DIR, "src", "web_impl.jl"); force = true)

Pkg.activate(BUILD_ENV)
Pkg.develop(path = SOURCE_DIR)
Pkg.instantiate()

using PackageCompiler

create_app(
    SOURCE_DIR,
    OUTPUT_DIR;
    executables = ["LissajousWebRuntime" => "julia_main"],
    force = true,
    incremental = true,
    include_lazy_artifacts = true,
)

println("Julia app created at $(OUTPUT_DIR)")
