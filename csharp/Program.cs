using MagentoVideoRecorder;

if (args.Contains("--serve", StringComparer.OrdinalIgnoreCase))
{
    await VideoService.RunAsync();
}
else
{
    await CsvVideoRecorder.RunAsync(args);
}
