rm lambdas/package/collect.py
rm lambdas/package/process.py
cp lambdas/collect.py lambdas/package/
cp lambdas/process.py lambdas/package/
cp -r lambdas/utils lambdas/package/
cd lambdas/package
zip -r ../lambdas.zip .