module LissajousWebRuntime

include("web_impl.jl")

function julia_main()::Cint
    try
        main()
        return 0
    catch error
        Base.display_error(stderr, error, catch_backtrace())
        return 1
    end
end

end
